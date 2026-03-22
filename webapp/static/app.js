const elements = {
  healthStatus: document.getElementById("health-status"),
  serviceDevice: document.getElementById("service-device"),
  historyCount: document.getElementById("history-count"),
  defaultConfidence: document.getElementById("default-confidence"),
  defaultImageSize: document.getElementById("default-image-size"),
  globalModel: document.getElementById("global-model"),
  globalConfidence: document.getElementById("global-confidence"),
  globalImageSize: document.getElementById("global-image-size"),
  refreshInfoButton: document.getElementById("refresh-info-button"),
  exportCsvButton: document.getElementById("export-csv-button"),
  exportXlsButton: document.getElementById("export-xls-button"),
  refreshHistoryButton: document.getElementById("refresh-history-button"),

  imageForm: document.getElementById("image-form"),
  imageInput: document.getElementById("image-input"),
  imageSelectedName: document.getElementById("image-selected-name"),
  imagePreview: document.getElementById("image-preview"),
  imagePreviewMeta: document.getElementById("image-preview-meta"),
  imagePrevButton: document.getElementById("image-prev-button"),
  imageNextButton: document.getElementById("image-next-button"),
  imageNavStatus: document.getElementById("image-nav-status"),
  imageSubmitButton: document.getElementById("image-submit-button"),
  imageResult: document.getElementById("image-result"),
  imageResultStatus: document.getElementById("image-result-status"),
  imageFileCount: document.getElementById("image-file-count"),
  imageCount: document.getElementById("image-count"),
  imageLatency: document.getElementById("image-latency"),
  imageFps: document.getElementById("image-fps"),
  imageClassSummary: document.getElementById("image-class-summary"),
  imageLinks: document.getElementById("image-links"),
  imageBatchBody: document.getElementById("image-batch-body"),
  imageTableBody: document.getElementById("image-table-body"),

  videoForm: document.getElementById("video-form"),
  videoInput: document.getElementById("video-input"),
  videoSelectedName: document.getElementById("video-selected-name"),
  videoSubmitButton: document.getElementById("video-submit-button"),
  videoResult: document.getElementById("video-result"),
  videoPreviewImage: document.getElementById("video-preview-image"),
  videoResultStatus: document.getElementById("video-result-status"),
  videoPreviewMeta: document.getElementById("video-preview-meta"),
  videoCount: document.getElementById("video-count"),
  videoFrames: document.getElementById("video-frames"),
  videoLatency: document.getElementById("video-latency"),
  videoFps: document.getElementById("video-fps"),
  videoLinks: document.getElementById("video-links"),

  cameraOpenButton: document.getElementById("camera-open-button"),
  cameraStartButton: document.getElementById("camera-start-button"),
  cameraStopButton: document.getElementById("camera-stop-button"),
  cameraCloseButton: document.getElementById("camera-close-button"),
  cameraLive: document.getElementById("camera-live"),
  cameraLiveStatus: document.getElementById("camera-live-status"),
  cameraResult: document.getElementById("camera-result"),
  cameraResultStatus: document.getElementById("camera-result-status"),
  cameraCount: document.getElementById("camera-count"),
  cameraLatency: document.getElementById("camera-latency"),
  cameraFps: document.getElementById("camera-fps"),
  cameraLoopStatus: document.getElementById("camera-loop-status"),

  historyTableBody: document.getElementById("history-table-body"),
};

const state = {
  models: [],
  defaultModelId: "",
  cameraStream: null,
  cameraDetecting: false,
  cameraCanvas: document.createElement("canvas"),
  historyRefreshTicks: 0,
  imageItems: [],
  activeImageIndex: 0,
  currentImageResult: null,
};

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json")
    ? await response.json()
    : { detail: await response.text() };

  if (!response.ok) {
    throw new Error(data.detail || "请求失败");
  }
  return data;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function cacheBust(url) {
  if (!url) {
    return "";
  }
  const joiner = url.includes("?") ? "&" : "?";
  return `${url}${joiner}t=${Date.now()}`;
}

function formatClassCounts(classCounts = {}) {
  const entries = Object.entries(classCounts);
  if (!entries.length) {
    return "未检测到目标";
  }
  return entries.map(([name, count]) => `${name} x ${count}`).join(" / ");
}

function setEmptyTableBody(body, colspan, text) {
  body.innerHTML = `
    <tr>
      <td colspan="${colspan}" class="empty-row">${text}</td>
    </tr>
  `;
}

function appendCommonFields(formData) {
  if (elements.globalModel.value) {
    formData.append("model_id", elements.globalModel.value);
  }
  if (elements.globalConfidence.value) {
    formData.append("confidence", elements.globalConfidence.value);
  }
  if (elements.globalImageSize.value) {
    formData.append("image_size", elements.globalImageSize.value);
  }
}

function createLink(label, href) {
  const link = document.createElement("a");
  link.href = href;
  link.target = "_blank";
  link.rel = "noreferrer";
  link.className = "file-link";
  link.textContent = label;
  return link;
}

function renderLinks(container, links) {
  container.innerHTML = "";
  const validLinks = links.filter((item) => item.href);
  if (!validLinks.length) {
    container.textContent = "暂无可用文件";
    return;
  }

  validLinks.forEach((item) => {
    container.appendChild(createLink(item.label, item.href));
  });
}

function renderImageTable(detections) {
  elements.imageTableBody.innerHTML = "";
  if (!detections.length) {
    setEmptyTableBody(elements.imageTableBody, 4, "当前图片没有检测到目标");
    return;
  }

  detections.forEach((item, index) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${index + 1}</td>
      <td>${item.display_name}</td>
      <td>${item.confidence}</td>
      <td>[${item.bbox.x1}, ${item.bbox.y1}, ${item.bbox.x2}, ${item.bbox.y2}]</td>
    `;
    elements.imageTableBody.appendChild(row);
  });
}

function renderImageBatchTable(items) {
  elements.imageBatchBody.innerHTML = "";
  if (!items.length) {
    setEmptyTableBody(elements.imageBatchBody, 4, "还没有图片处理结果");
    return;
  }

  items.forEach((item, index) => {
    const row = document.createElement("tr");
    if (index === state.activeImageIndex) {
      row.classList.add("active-row");
    }

    const nameCell = document.createElement("td");
    nameCell.textContent = item.source_name || `image_${index + 1}.jpg`;

    const countCell = document.createElement("td");
    countCell.textContent = String(item.summary?.detection_count ?? 0);

    const summaryCell = document.createElement("td");
    summaryCell.textContent = formatClassCounts(item.summary?.class_counts || {});

    const actionsCell = document.createElement("td");
    actionsCell.className = "actions-cell";

    const viewButton = document.createElement("button");
    viewButton.type = "button";
    viewButton.className = "table-button";
    viewButton.textContent = "查看";
    viewButton.addEventListener("click", () => {
      setActiveImageItem(index);
    });

    actionsCell.appendChild(viewButton);
    if (item.source_url) {
      actionsCell.appendChild(createLink("原图", item.source_url));
    }
    if (item.result_url) {
      actionsCell.appendChild(createLink("结果", item.result_url));
    }

    row.appendChild(nameCell);
    row.appendChild(countCell);
    row.appendChild(summaryCell);
    row.appendChild(actionsCell);
    elements.imageBatchBody.appendChild(row);
  });
}

function renderHistory(records) {
  elements.historyTableBody.innerHTML = "";
  if (!records.length) {
    setEmptyTableBody(elements.historyTableBody, 6, "还没有历史记录");
    return;
  }

  records.forEach((record) => {
    const row = document.createElement("tr");

    const createdCell = document.createElement("td");
    createdCell.textContent = record.created_at || "-";

    const typeCell = document.createElement("td");
    typeCell.textContent = record.task_type || "-";

    const sourceCell = document.createElement("td");
    sourceCell.textContent = record.source_name || "-";

    const modelCell = document.createElement("td");
    modelCell.textContent = record.model_label || "-";

    const countCell = document.createElement("td");
    countCell.textContent = String(record.summary?.detection_count ?? 0);

    const actionsCell = document.createElement("td");
    actionsCell.className = "actions-cell";

    const actionLinks = [
      ["结果", record.result_url],
      ["预览", record.preview_url],
      ["源文件", record.source_url],
      ["CSV", record.csv_url],
      ["详情", record.meta_url],
    ].filter((item) => item[1]);

    if (!actionLinks.length) {
      actionsCell.textContent = "-";
    } else {
      actionLinks.forEach(([label, href]) => {
        actionsCell.appendChild(createLink(label, href));
      });
    }

    row.appendChild(createdCell);
    row.appendChild(typeCell);
    row.appendChild(sourceCell);
    row.appendChild(modelCell);
    row.appendChild(countCell);
    row.appendChild(actionsCell);
    elements.historyTableBody.appendChild(row);
  });
}

function populateModels(models, defaultModelId) {
  const previousValue = elements.globalModel.value;
  elements.globalModel.innerHTML = "";

  models.forEach((model) => {
    const option = document.createElement("option");
    option.value = model.id;
    option.textContent = model.label;
    elements.globalModel.appendChild(option);
  });

  if (previousValue && models.some((item) => item.id === previousValue)) {
    elements.globalModel.value = previousValue;
  } else if (defaultModelId) {
    elements.globalModel.value = defaultModelId;
  }
}

function setHealth(ok, text) {
  elements.healthStatus.textContent = text;
  elements.healthStatus.classList.toggle("online", ok);
  elements.healthStatus.classList.toggle("offline", !ok);
}

async function loadBootstrap() {
  try {
    const [health, info] = await Promise.all([
      fetchJson("/api/health"),
      fetchJson("/api/info"),
    ]);

    const service = info.service || {};
    state.models = service.models || [];
    state.defaultModelId = service.default_model_id || "";

    setHealth(health.status === "ok", health.status === "ok" ? "在线" : "异常");
    elements.serviceDevice.textContent = service.device || "-";
    elements.historyCount.textContent = String(service.history_count || 0);
    elements.defaultConfidence.textContent = String(service.default_confidence ?? "-");
    elements.defaultImageSize.textContent = String(service.default_image_size ?? "-");
    elements.globalConfidence.placeholder = String(service.default_confidence ?? "");
    elements.globalImageSize.placeholder = String(service.default_image_size ?? "");
    populateModels(state.models, state.defaultModelId);
  } catch (error) {
    setHealth(false, "连接失败");
  }
}

async function loadHistory() {
  try {
    const data = await fetchJson("/api/history?limit=60");
    renderHistory(data.records || []);
    elements.historyCount.textContent = String(data.count || 0);
  } catch (error) {
    setEmptyTableBody(elements.historyTableBody, 6, error.message);
  }
}

function setImageSelectionPreview(files) {
  if (!files.length) {
    elements.imageSelectedName.textContent = "尚未选择文件";
    elements.imagePreview.removeAttribute("src");
    elements.imagePreviewMeta.textContent = "等待上传";
    return;
  }

  const [firstFile] = files;
  if (files.length === 1) {
    elements.imageSelectedName.textContent = firstFile.name;
    elements.imagePreviewMeta.textContent = `${Math.round(firstFile.size / 1024)} KB`;
  } else {
    elements.imageSelectedName.textContent = `已选择 ${files.length} 张图片`;
    elements.imagePreviewMeta.textContent = `当前预览首张: ${firstFile.name}`;
  }

  const reader = new FileReader();
  reader.onload = (event) => {
    elements.imagePreview.src = event.target.result;
  };
  reader.readAsDataURL(firstFile);
}

function normalizeImageResult(result) {
  if (result.items) {
    return result;
  }

  return {
    ...result,
    summary: {
      ...(result.summary || {}),
      image_count: 1,
    },
    items: [
      {
        source_name: result.source_name,
        summary: result.summary || {},
        detections: result.detections || [],
        source_url: result.source_url,
        result_url: result.result_url,
      },
    ],
    preview_url: result.result_url,
  };
}

function updateImageNavigator() {
  const total = state.imageItems.length;
  const hasItems = total > 0;
  const isBatch = total > 1;

  elements.imagePrevButton.disabled = !isBatch || state.activeImageIndex <= 0;
  elements.imageNextButton.disabled = !isBatch || state.activeImageIndex >= total - 1;

  if (!hasItems) {
    elements.imageNavStatus.textContent = "等待批量结果";
    return;
  }

  elements.imageNavStatus.textContent = isBatch
    ? `第 ${state.activeImageIndex + 1} / ${total} 张`
    : "单图模式";
}

function setActiveImageItem(index) {
  if (!state.imageItems.length) {
    return;
  }

  if (index < 0 || index >= state.imageItems.length) {
    return;
  }

  state.activeImageIndex = index;
  const activeItem = state.imageItems[index];
  const total = state.imageItems.length;
  const detectionCount = activeItem.summary?.detection_count ?? 0;

  if (activeItem.source_url) {
    elements.imagePreview.src = cacheBust(activeItem.source_url);
  } else {
    elements.imagePreview.removeAttribute("src");
  }

  if (activeItem.result_url) {
    elements.imageResult.src = cacheBust(activeItem.result_url);
  } else {
    elements.imageResult.removeAttribute("src");
  }

  elements.imagePreviewMeta.textContent = `${activeItem.source_name || `图片 ${index + 1}`} | ${detectionCount} 个目标`;
  elements.imageResultStatus.textContent = total > 1
    ? `批量处理完成，共 ${total} 张，当前查看第 ${index + 1} 张`
    : `已保存 ${activeItem.source_name || "检测结果"}`;

  renderImageTable(activeItem.detections || []);
  renderImageBatchTable(state.imageItems);
  updateImageNavigator();
  renderLinks(elements.imageLinks, [
    { label: "查看当前原图", href: activeItem.source_url },
    { label: "查看当前结果", href: activeItem.result_url },
    { label: total > 1 ? "下载批量 CSV" : "下载 CSV", href: state.currentImageResult?.csv_url },
    { label: "查看详情", href: state.currentImageResult?.meta_url },
  ]);
}

function renderImageResult(result) {
  const normalized = normalizeImageResult(result);
  const items = normalized.items || [];

  state.currentImageResult = normalized;
  state.imageItems = items;
  state.activeImageIndex = 0;

  elements.imageFileCount.textContent = String(normalized.summary?.image_count || items.length || 0);
  elements.imageCount.textContent = String(normalized.summary?.detection_count || 0);
  elements.imageLatency.textContent = `${normalized.summary?.latency_seconds || 0} s`;
  elements.imageFps.textContent = String(normalized.summary?.fps || 0);
  elements.imageClassSummary.textContent = formatClassCounts(normalized.summary?.class_counts || {});

  if (!items.length) {
    elements.imagePreview.removeAttribute("src");
    elements.imageResult.removeAttribute("src");
    setEmptyTableBody(elements.imageBatchBody, 4, "还没有图片处理结果");
    setEmptyTableBody(elements.imageTableBody, 4, "当前图片没有检测到目标");
    updateImageNavigator();
    renderLinks(elements.imageLinks, []);
    return;
  }

  setActiveImageItem(0);
}

elements.imageInput.addEventListener("change", (event) => {
  const files = Array.from(event.target.files || []);
  setImageSelectionPreview(files);
});

elements.imagePrevButton.addEventListener("click", () => {
  setActiveImageItem(state.activeImageIndex - 1);
});

elements.imageNextButton.addEventListener("click", () => {
  setActiveImageItem(state.activeImageIndex + 1);
});

elements.videoInput.addEventListener("change", (event) => {
  const [file] = event.target.files || [];
  elements.videoSelectedName.textContent = file ? file.name : "尚未选择文件";
});

elements.imageForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const files = Array.from(elements.imageInput.files || []);
  if (!files.length) {
    elements.imageResultStatus.textContent = "请先选择图片";
    return;
  }

  const formData = new FormData();
  const isBatch = files.length > 1;
  if (isBatch) {
    files.forEach((file) => formData.append("files", file));
  } else {
    formData.append("file", files[0]);
  }
  appendCommonFields(formData);

  elements.imageSubmitButton.disabled = true;
  elements.imageResultStatus.textContent = isBatch ? "批量处理中..." : "检测中...";

  try {
    const result = await fetchJson(
      isBatch ? "/api/predict/images-batch" : "/api/predict/image",
      {
        method: "POST",
        body: formData,
      },
    );
    renderImageResult(result);
    await loadHistory();
  } catch (error) {
    elements.imageResultStatus.textContent = error.message;
  } finally {
    elements.imageSubmitButton.disabled = false;
  }
});

elements.videoForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const [file] = elements.videoInput.files || [];
  if (!file) {
    elements.videoResultStatus.textContent = "请先选择视频";
    return;
  }

  const formData = new FormData();
  formData.append("file", file);
  appendCommonFields(formData);

  elements.videoSubmitButton.disabled = true;
  elements.videoResultStatus.textContent = "视频处理中，这一步可能会稍慢一些...";

  try {
    const result = await fetchJson("/api/predict/video", {
      method: "POST",
      body: formData,
    });

    elements.videoResult.src = cacheBust(result.result_url);
    elements.videoResult.load();
    elements.videoPreviewImage.src = cacheBust(result.preview_url);
    elements.videoResultStatus.textContent = `处理完成: ${result.source_name}`;
    elements.videoPreviewMeta.textContent = formatClassCounts(result.summary?.class_counts || {});
    elements.videoCount.textContent = String(result.summary?.detection_count || 0);
    elements.videoFrames.textContent = String(result.summary?.frame_count || 0);
    elements.videoLatency.textContent = `${result.summary?.latency_seconds || 0} s`;
    elements.videoFps.textContent = String(result.summary?.fps || 0);

    renderLinks(elements.videoLinks, [
      { label: "查看原视频", href: result.source_url },
      { label: "查看结果视频", href: result.result_url },
      { label: "查看首帧", href: result.preview_url },
      { label: "下载逐帧 CSV", href: result.csv_url },
      { label: "查看详情", href: result.meta_url },
    ]);
    await loadHistory();
  } catch (error) {
    elements.videoResultStatus.textContent = error.message;
  } finally {
    elements.videoSubmitButton.disabled = false;
  }
});

async function ensureCameraReady() {
  const video = elements.cameraLive;

  if (video.readyState < 2) {
    await new Promise((resolve) => {
      const onLoadedData = () => {
        video.removeEventListener("loadeddata", onLoadedData);
        resolve();
      };
      video.addEventListener("loadeddata", onLoadedData);
    });
  }

  try {
    await video.play();
  } catch (error) {
    // Browsers can reject autoplay even after stream binding.
  }

  await sleep(250);
}

async function openCamera() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    throw new Error("当前浏览器不支持摄像头接口");
  }

  if (state.cameraStream) {
    await ensureCameraReady();
    elements.cameraLive.dataset.ready = "true";
    elements.cameraLiveStatus.textContent = "摄像头已打开";
    return;
  }

  state.cameraStream = await navigator.mediaDevices.getUserMedia({
    video: true,
    audio: false,
  });

  elements.cameraLive.srcObject = state.cameraStream;
  await ensureCameraReady();
  elements.cameraLive.dataset.ready = "true";
  elements.cameraLiveStatus.textContent = "摄像头已打开";
}

function closeCamera() {
  state.cameraDetecting = false;

  if (state.cameraStream) {
    state.cameraStream.getTracks().forEach((track) => track.stop());
    state.cameraStream = null;
  }

  elements.cameraLive.pause();
  elements.cameraLive.srcObject = null;
  elements.cameraLive.dataset.ready = "false";
  elements.cameraLiveStatus.textContent = "摄像头已关闭";
  elements.cameraLoopStatus.textContent = "已关闭";
}

async function captureCameraBlob() {
  const video = elements.cameraLive;
  if (!video.videoWidth || !video.videoHeight) {
    throw new Error("摄像头画面还没有准备好");
  }

  state.cameraCanvas.width = video.videoWidth;
  state.cameraCanvas.height = video.videoHeight;
  const context = state.cameraCanvas.getContext("2d");
  context.drawImage(video, 0, 0, state.cameraCanvas.width, state.cameraCanvas.height);

  return new Promise((resolve, reject) => {
    state.cameraCanvas.toBlob((blob) => {
      if (!blob) {
        reject(new Error("无法抓取摄像头画面"));
        return;
      }
      resolve(blob);
    }, "image/jpeg", 0.92);
  });
}

async function cameraLoop() {
  while (state.cameraDetecting) {
    try {
      const blob = await captureCameraBlob();
      const formData = new FormData();
      formData.append("file", blob, `camera_${Date.now()}.jpg`);
      appendCommonFields(formData);

      const result = await fetchJson("/api/predict/camera-frame", {
        method: "POST",
        body: formData,
      });

      elements.cameraResult.src = cacheBust(result.result_url);
      elements.cameraResultStatus.textContent = `最近一次保存: ${result.created_at}`;
      elements.cameraCount.textContent = String(result.summary?.detection_count || 0);
      elements.cameraLatency.textContent = `${result.summary?.latency_seconds || 0} s`;
      elements.cameraFps.textContent = String(result.summary?.fps || 0);
      elements.cameraLoopStatus.textContent = formatClassCounts(result.summary?.class_counts || {});

      state.historyRefreshTicks += 1;
      if (state.historyRefreshTicks % 5 === 0) {
        await loadHistory();
      }
    } catch (error) {
      elements.cameraResultStatus.textContent = error.message;
    }

    await sleep(700);
  }
}

elements.cameraOpenButton.addEventListener("click", async () => {
  try {
    await openCamera();
  } catch (error) {
    elements.cameraResultStatus.textContent = error.message;
  }
});

elements.cameraStartButton.addEventListener("click", async () => {
  try {
    await openCamera();
  } catch (error) {
    elements.cameraResultStatus.textContent = error.message;
    return;
  }

  if (state.cameraDetecting) {
    return;
  }

  state.cameraDetecting = true;
  elements.cameraLiveStatus.textContent = "实时检测中";
  elements.cameraLoopStatus.textContent = "运行中";
  cameraLoop();
});

elements.cameraStopButton.addEventListener("click", () => {
  state.cameraDetecting = false;
  elements.cameraLiveStatus.textContent = state.cameraStream ? "摄像头已打开" : "已停止";
  elements.cameraLoopStatus.textContent = "已停止";
  loadHistory();
});

elements.cameraCloseButton.addEventListener("click", () => {
  closeCamera();
  loadHistory();
});

elements.refreshInfoButton.addEventListener("click", async () => {
  await loadBootstrap();
  await loadHistory();
});

elements.refreshHistoryButton.addEventListener("click", loadHistory);

elements.exportCsvButton.addEventListener("click", () => {
  window.open("/api/history/export?format=csv", "_blank");
});

elements.exportXlsButton.addEventListener("click", () => {
  window.open("/api/history/export?format=xls", "_blank");
});

window.addEventListener("beforeunload", () => {
  closeCamera();
});

async function init() {
  await loadBootstrap();
  await loadHistory();
}

init();
