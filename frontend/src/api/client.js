import axios from "axios";

const api = axios.create({
  baseURL: "/api",
});

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await api.post("/upload", formData);
  return response.data;
}

export async function verifyDocument(documentId) {
  const response = await api.post(`/verify/${documentId}`);
  return response.data;
}

export async function getResults(documentId) {
  const response = await api.get(`/results/${documentId}`);
  return response.data;
}

export async function getHistory(params = {}) {
  const response = await api.get("/history", { params });
  return response.data;
}

export async function healthCheck() {
  const response = await api.get("/health");
  return response.data;
}

export default api;
