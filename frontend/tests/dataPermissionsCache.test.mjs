import assert from "node:assert/strict";
import test from "node:test";
import { apiCacheIdentity, readApiCache, writeApiCache } from "../src/app/apiCache.js";
import { fetchJson } from "../src/app/utils.js";

const values=new Map();
globalThis.document={cookie:"newabby_data_cache=w-fixture-a"};
globalThis.window={sessionStorage:{
  getItem:key=>values.get(key)??null,setItem:(key,value)=>values.set(key,value),removeItem:key=>values.delete(key),
  key:index=>[...values.keys()][index],get length(){return values.size;}
}};
const url="/api/vue/lists";

test("private API caches cannot cross accounts or accept pre-isolation keys",()=>{
  values.clear();
  values.set(`speakeasy.apiCache:${url}`,JSON.stringify({createdAt:Date.now(),payload:{secret:"legacy"}}));
  assert.equal(readApiCache(url),null);
  writeApiCache(url,{owner:"a"});
  document.cookie="newabby_data_cache=w-fixture-b";
  assert.equal(readApiCache(url),null);
  writeApiCache(url,{owner:"b"});
  document.cookie="newabby_data_cache=w-fixture-a";
  assert.deepEqual(readApiCache(url),{owner:"a"});
});

test("no cache marker and read-only other-owner views never cache private data",()=>{
  for(const identity of ["","r-fixture-readonly"]){
    values.clear(); document.cookie=identity?`newabby_data_cache=${identity}`:"";
    writeApiCache(url,{owner:"not-cacheable"});
    assert.equal(values.size,0); assert.equal(readApiCache(url),null);
  }
});

test("late responses from a previous account are rejected before rendering or caching",async()=>{
  document.cookie="newabby_data_cache=w-old"; values.clear();
  let resolve;
  globalThis.fetch=()=>new Promise(done=>{resolve=done;});
  const pending=fetchJson(url);
  document.cookie="newabby_data_cache=w-new";
  resolve(new Response(JSON.stringify({owner:"old"}),{headers:{"Content-Type":"application/json","X-Newabby-Scope":"w-old"}}));
  await assert.rejects(pending,error=>error.status===409);
  assert.equal(values.size,0);
});

test("a mismatched server scope is never stored under the current cookie",async()=>{
  document.cookie="newabby_data_cache=w-current"; values.clear();
  globalThis.fetch=async()=>new Response(JSON.stringify({owner:"other"}),{headers:{"Content-Type":"application/json","X-Newabby-Scope":"r-other"}});
  await assert.rejects(fetchJson(url),error=>error.status===409);
  assert.equal(apiCacheIdentity(),"w-current"); assert.equal(values.size,0);
});
