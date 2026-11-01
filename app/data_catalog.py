"""Create the shared catalog from verified official source rows, never private rows."""
import json
from urllib.parse import urlparse

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.dialects.mysql import insert as mysql_insert

from app.data_context import PUBLIC_OWNER, current_data_context
from app.models import Word, WordList, WordListGroup, WordListItem

TEXT_FIELDS=("phonetic","part_of_speech","english_definition","chinese_definition","english_example","alternate_spellings")
URL_FIELDS=("american_audio_url","british_audio_url","english_definition_audio_url","english_example_audio_url")


def official_values(row):
    spelling=str(row.get("word") or "").strip()
    if not spelling or len(spelling)>128:
        raise ValueError("Official source contains an invalid spelling")
    values={"word":spelling,"source":"spb-public-source","enrichment_status":"pending"}
    for field in TEXT_FIELDS:
        value=row.get(field)
        if value: values[field]=str(value)
    for field in URL_FIELDS:
        value=str(row.get(field) or "").strip()
        parsed=urlparse(value)
        if parsed.scheme=="https" and parsed.hostname=="cdn.spbcn.org":
            values[field]=value
    # Metadata is reconstructed, not copied from an old user's note/locks/media.
    values["note"]=json.dumps({key:row[key] for key in ("spb_word_id","spb_product_id","spb_flag","spb_product_flag","spb_kernel",
        "spb_category_key","spb_category_title","spb_category_order") if key in row},ensure_ascii=False)
    return values


def seed_public_catalog(db,sources):
    context=current_data_context()
    if not context or not context.public_write or not context.is_admin:
        raise HTTPException(403,"只有经过验证的公共词库维护流程可写入。")
    if not sources or any(not source.get("verified_official") or not source.get("rows") for source in sources):
        raise ValueError("Every public source must be nonempty and verified official")
    receipts=[]
    # Keep this privileged migration path bounded for real catalogs. The only
    # Core inserts below use official_values(), a fixed public owner, and IDs
    # read back from the PUBLIC catalog. No private row is ever used as input.
    words_by_key={word.word.casefold():word.id for word in db.scalars(select(Word).where(Word.owner_key==PUBLIC_OWNER))}
    for source in sources:
        name=str(source["name"]).strip()
        if not name: raise ValueError("Missing public source name")
        group_name=str(source.get("group_name") or name).strip()
        group=db.scalar(select(WordListGroup).where(WordListGroup.owner_key==PUBLIC_OWNER,WordListGroup.name==group_name))
        if not group:
            group=WordListGroup(name=group_name)
            db.add(group)
            db.flush()
        lists=db.scalars(select(WordList).where(WordList.owner_key==PUBLIC_OWNER,WordList.group_id==group.id,
            (WordList.name==name) | WordList.name.startswith(name+'-'))
            .order_by(WordList.sequence_offset,WordList.id)).all()
        existing=set(db.scalars(select(Word.word).join(WordListItem,WordListItem.word_id==Word.id)
            .where(WordListItem.word_list_id.in_([item.id for item in lists]))))
        offset=sum(db.scalar(select(func.count(WordListItem.id)).where(WordListItem.word_list_id==item.id)) or 0 for item in lists)
        missing=[]
        existing_keys={word.casefold() for word in existing}
        for row in source["rows"]:
            values=official_values(row)
            if values["word"].casefold() in existing_keys: continue
            existing.add(values["word"])
            existing_keys.add(values["word"].casefold())
            missing.append(values)
        added=0
        for start in range(0,len(missing),500):
            target=WordList(name=f"{name}-{len(lists)+1}",group_id=group.id,sequence_offset=offset)
            db.add(target)
            db.flush()
            batch=missing[start:start+500]
            fresh=[values for values in batch if values['word'].casefold() not in words_by_key]
            if fresh:
                fields=set(TEXT_FIELDS+URL_FIELDS+("word","note","source","enrichment_status"))
                rows=[{**{field:values.get(field) for field in fields},"owner_key":PUBLIC_OWNER} for values in fresh]
                table=Word.__table__
                if db.get_bind().dialect.name=='mysql':
                    statement=mysql_insert(table)
                    # MySQL's spelling collation can merge case/accent aliases;
                    # an existing public word is retained, never overwritten.
                    statement=statement.on_duplicate_key_update(owner_key=PUBLIC_OWNER)
                else:
                    statement=table.insert()
                db.connection().execute(statement,rows)
                for word in db.scalars(select(Word).where(Word.owner_key==PUBLIC_OWNER,Word.word.in_([values['word'] for values in fresh]))):
                    words_by_key[word.word.casefold()]=word.id
            links=[]; linked=set()
            for values in batch:
                key=values['word'].casefold()
                word_id=words_by_key.get(key)
                if word_id is None:
                    word_id=db.scalar(select(Word.id).where(Word.owner_key==PUBLIC_OWNER,Word.word==values['word']))
                    if word_id is None: raise ValueError('An official spelling could not be resolved')
                    words_by_key[key]=word_id
                if word_id in linked: continue
                linked.add(word_id)
                links.append({'owner_key':PUBLIC_OWNER,'word_list_id':target.id,'word_id':word_id})
            if links: db.connection().execute(WordListItem.__table__.insert(),links)
            added+=len(links)
            offset+=len(links)
            lists.append(target)
        receipts.append({"name":name,"added":added,"list_count":len(lists),"word_count":len(existing)})
    db.commit()
    return receipts
