/** Version de produccion de la API del parcial 2. Ajustar cuando se despliegue. */
export const API_URL = ['localhost', '127.0.0.1', '[::1]'].includes(location.hostname)
  ? 'http://127.0.0.1:8000/api/v1'
  : 'https://gangaclothes-parcial2-live.onrender.com/api/v1';
