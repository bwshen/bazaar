/*
 * App Actions
 *
 * Actions change things in your application
 * Since this boilerplate uses a uni-directional data flow, specifically redux,
 * we have these actions which are the only way your application interacts with
 * your application state. This guarantees that your state is up to date and nobody
 * messes it up weirdly somewhere.
 *
 * To add a new Action:
 * 1) Import your constant
 * 2) Add a function like this:
 *    export function yourAction(var) {
 *        return { type: YOUR_ACTION_CONSTANT, var: var }
 *    }
 */

import {
  INIT_USER,
} from './constants';
import axios from 'axios';
import {HOST} from "../../constants/conf";

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length == 2) return parts.pop().split(';').shift();
}

export const fetchUserIfExists = function() {

    return (dispatch, getState) => {
      const sessionId = getCookie('sessionid');
      if (!!sessionId) {
        // hit profile endpoint, retrieve owner sid
        axios.get(HOST+"/api/profile/", {
          withCredentials: true,
        }).then((response) => {
          dispatch(initUser(response.data.sid, response.data.auth_token));
        });
      }
    };
}

export const initUser = function(sid, authToken) {
  return {
    type: INIT_USER,
    sid,
    authToken,
  };
}
