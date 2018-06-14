import axios from 'axios';
import cloner from 'cloner';

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length == 2) return parts.pop().split(';').shift();
}

export const API = {
  get: function(url, opt_config) {
    const authToken = getCookie('authtoken');
    if (!authToken) {
      throw new Error('missing authToken');
    }
    return axios.get(url, {
      headers: {'Authorization': `Token ${authToken}`}, withCredentials: true,
    });
  },

  post: function(url, opt_data, opt_config) {
    const authToken = getCookie('authtoken');
    if (!authToken) {
      throw new Error('missing authToken');
    }
    return axios.post(url, opt_data || {}, cloner.deep.merge({
      headers: {'Authorization': `Token ${authToken}`}, 'withCredentials': true,
    }, opt_config|| {}));
  }
}


