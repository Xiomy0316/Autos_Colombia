/**
 * Entorno de producción (build de Docker / Render): la API vive detrás del
 * mismo origen, así que se llama a `/api` y nginx la reverse-proxya hacia el
 * servicio del backend (`API_URL`).
 */
export const environment = {
  production: true,
  apiUrl: '/api',
};
