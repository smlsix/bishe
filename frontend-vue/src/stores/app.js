import { computed, ref } from 'vue'

const service = ref(null)
const selectedModel = ref('')
const confidence = ref('')
const imageSize = ref('')

const models = computed(() => service.value?.models || [])

function applyService(servicePayload) {
  service.value = servicePayload || null
  if (!servicePayload) {
    return
  }

  const availableModels = servicePayload.models || []
  if (!selectedModel.value || !availableModels.some((item) => item.id === selectedModel.value)) {
    selectedModel.value = servicePayload.default_model_id || ''
  }
  if (confidence.value === '' && servicePayload.default_confidence !== undefined) {
    confidence.value = String(servicePayload.default_confidence)
  }
  if (imageSize.value === '' && servicePayload.default_image_size !== undefined) {
    imageSize.value = String(servicePayload.default_image_size)
  }
}

function appendCommonFields(formData) {
  if (selectedModel.value) {
    formData.append('model_id', selectedModel.value)
  }
  if (confidence.value !== '') {
    formData.append('confidence', confidence.value)
  }
  if (imageSize.value !== '') {
    formData.append('image_size', imageSize.value)
  }
}

export function useAppStore() {
  return {
    service,
    models,
    selectedModel,
    confidence,
    imageSize,
    applyService,
    appendCommonFields,
  }
}
