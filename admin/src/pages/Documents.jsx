import { useEffect, useState } from "react";
import { getDocuments, uploadDocument, triggerReindex, createCrop } from "../api";

export default function Documents() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState(null);
  const [reindexing, setReindexing] = useState(false);
  const [reindexMsg, setReindexMsg] = useState(null);
  const [newCropName, setNewCropName] = useState("");
  const [newCropLabel, setNewCropLabel] = useState("");
  const [creatingCrop, setCreatingCrop] = useState(false);
  const [cropMsg, setCropMsg] = useState(null);
  const [selectedCrop, setSelectedCrop] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);

  const loadData = () => {
    getDocuments()
      .then(setData)
      .catch((e) => setError(e.message));
  };

  useEffect(loadData, []);

  const handleUpload = async () => {
    if (!selectedCrop || !selectedFile) return;
    setUploading(true);
    setUploadMsg(null);
    try {
      const result = await uploadDocument(selectedCrop, selectedFile);
      setUploadMsg({ ok: true, text: result.message });
      setSelectedFile(null);
      loadData();
    } catch (e) {
      setUploadMsg({ ok: false, text: e.message });
    } finally {
      setUploading(false);
    }
  };

  const handleReindex = async () => {
    setReindexing(true);
    setReindexMsg(null);
    try {
      const result = await triggerReindex();
      setReindexMsg({ ok: true, text: result.message });
      loadData();
    } catch (e) {
      setReindexMsg({ ok: false, text: e.message });
    } finally {
      setReindexing(false);
    }
  };

  const handleCreateCrop = async () => {
    if (!newCropName || !newCropLabel) return;
    setCreatingCrop(true);
    setCropMsg(null);
    try {
      const result = await createCrop(newCropName, newCropLabel);
      setCropMsg({ ok: true, text: result.message });
      setNewCropName("");
      setNewCropLabel("");
      loadData();
    } catch (e) {
      setCropMsg({ ok: false, text: e.message });
    } finally {
      setCreatingCrop(false);
    }
  };

  if (error) return <p className="text-red-500">Error: {error}</p>;
  if (!data) return <p className="text-gray-400">Cargando...</p>;

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Documentos</h2>

      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
        <h3 className="text-lg font-semibold text-gray-700 mb-4">Subir nuevo documento</h3>
        <div className="flex items-center gap-4">
          <select
            value={selectedCrop}
            onChange={(e) => setSelectedCrop(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          >
            <option value="">Seleccionar cultivo...</option>
            {data.crops.map((c) => (
              <option key={c.name} value={c.name}>
                {c.label} ({c.name})
              </option>
            ))}
          </select>
          <input
            type="file"
            accept=".pdf"
            onChange={(e) => setSelectedFile(e.target.files[0])}
            className="text-sm"
          />
          <button
            onClick={handleUpload}
            disabled={uploading || !selectedCrop || !selectedFile}
            className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {uploading ? "Subiendo..." : "Subir PDF"}
          </button>
        </div>
        {uploadMsg && (
          <p className={`mt-3 text-sm ${uploadMsg.ok ? "text-green-600" : "text-red-500"}`}>
            {uploadMsg.text}
          </p>
        )}
      </div>
      
      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
        <h3 className="text-lg font-semibold text-gray-700 mb-4">Reindexación</h3>
        <p className="text-sm text-gray-500 mb-4">
          Procesa documentos nuevos y los agrega al índice de búsqueda sin reindexar los existentes.
        </p>
        <button
          onClick={handleReindex}
          disabled={reindexing}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {reindexing ? "Indexando..." : "🔄 Ejecutar reindexación"}
        </button>
        {reindexMsg && (
          <p className={`mt-3 text-sm ${reindexMsg.ok ? "text-green-600" : "text-red-500"}`}>
            {reindexMsg.text}
          </p>
        )}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
        <h3 className="text-lg font-semibold text-gray-700 mb-4">Agregar nuevo cultivo</h3>
        <div className="flex items-center gap-4">
          <input
            type="text"
            placeholder="Nombre en inglés (ej: tomato)"
            value={newCropName}
            onChange={(e) => setNewCropName(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm flex-1"
          />
          <input
            type="text"
            placeholder="Etiqueta en español (ej: tomate)"
            value={newCropLabel}
            onChange={(e) => setNewCropLabel(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm flex-1"
          />
          <button
            onClick={handleCreateCrop}
            disabled={creatingCrop || !newCropName || !newCropLabel}
            className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {creatingCrop ? "Creando..." : "🌿 Crear cultivo"}
          </button>
        </div>
        {cropMsg && (
          <p className={`mt-3 text-sm ${cropMsg.ok ? "text-green-600" : "text-red-500"}`}>
            {cropMsg.text}
          </p>
        )}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-3 text-gray-500 font-medium">Archivo</th>
              <th className="text-left px-4 py-3 text-gray-500 font-medium">Cultivo</th>
              <th className="text-center px-4 py-3 text-gray-500 font-medium">Indexado</th>
              <th className="text-left px-4 py-3 text-gray-500 font-medium">Fecha</th>
            </tr>
          </thead>
          <tbody>
            {data.documents.map((doc) => (
              <tr key={doc.id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-3">{doc.file_name}</td>
                <td className="px-4 py-3">{doc.crops?.label || "?"}</td>
                <td className="px-4 py-3 text-center">{doc.is_indexed ? "✅" : "❌"}</td>
                <td className="px-4 py-3 text-gray-400">
                  {new Date(doc.created_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}