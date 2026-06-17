import { useWordAudio } from './useWordAudio.js';
import { useWordDetailLifecycle } from './useWordDetailLifecycle.js';
import { useWordEditing } from './useWordEditing.js';
import { useWordImages } from './useWordImages.js';
import { useWordNavigation } from './useWordNavigation.js';
import { createWordDetailToolContext } from '../wordDetailToolContext.js';

export function useWordDetail({ data, loadRoute }) {
  const editing = useWordEditing({ data });
  const images = useWordImages({ data, loadRoute });
  const audio = useWordAudio({ data, loadRoute });
  const navigation = useWordNavigation({ data });
  const lifecycle = useWordDetailLifecycle({
    data,
    loadRoute,
    resetImageTools: images.resetImageTools,
    resetAudioTools: audio.resetAudioTools,
  });

  return createWordDetailToolContext({ editing, images, audio, navigation, lifecycle });
}
