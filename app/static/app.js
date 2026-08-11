async function getUploadUrl(name, file, fileType) {
  const response = await fetch("/api/upload-url", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      name,
      filename: file.name,
      content_type: file.type,
      file_type: fileType
    })
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Could not create upload URL");
  return data;
}

async function uploadFile(upload, file) {
  const response = await fetch(upload.upload_url, {
    method: "PUT",
    headers: {"Content-Type": file.type},
    body: file
  });
  if (!response.ok) throw new Error(`Upload failed for ${file.name}`);
  return upload.object_key;
}

function getVideoDuration(file) {
  return new Promise((resolve, reject) => {
    const video = document.createElement("video");
    video.preload = "metadata";
    video.onloadedmetadata = () => {
      URL.revokeObjectURL(video.src);
      resolve(video.duration);
    };
    video.onerror = () => reject(new Error("Could not read video metadata"));
    video.src = URL.createObjectURL(file);
  });
}

document.getElementById("applicationForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const status = document.getElementById("status");
  const name = document.getElementById("name").value.trim();
  const photo = document.getElementById("photo").files[0];
  const cv = document.getElementById("cv").files[0];
  const video = document.getElementById("video").files[0];

  status.textContent = "Uploading...";

  try {
    if (!name || !photo || !cv) throw new Error("Name, photo and CV are required.");

    if (video) {
      const duration = await getVideoDuration(video);
      if (duration > 30.0) {
        throw new Error("Video must not exceed 30 seconds.");
      }
    }

    const photoUpload = await getUploadUrl(name, photo, "photo");
    const cvUpload = await getUploadUrl(name, cv, "cv");

    const photoKey = await uploadFile(photoUpload, photo);
    const cvKey = await uploadFile(cvUpload, cv);

    let videoKey = null;
    if (video) {
      const videoUpload = await getUploadUrl(name, video, "video");
      videoKey = await uploadFile(videoUpload, video);
    }

    const response = await fetch("/api/applications", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        name,
        photo_key: photoKey,
        cv_key: cvKey,
        video_key: videoKey
      })
    });

    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Submission failed");

    status.textContent = `Application submitted successfully. ID: ${result.id}`;
    event.target.reset();
  } catch (error) {
    status.textContent = error.message;
  }
});
