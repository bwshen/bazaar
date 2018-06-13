/*
 * AppReducer
 *
 * The reducer takes care of our data. Using actions, we can change our
 * application state.
 * To add a new action, add it to the switch statement in the reducer function
 *
 * Example:
 * case YOUR_ACTION_CONSTANT:
 *   return state.set('yourStateVariable', true);
 */

import { combineReducers } from 'redux-immutable';

import {
  INIT_USER,
} from './constants';

const initUserState = {
  sid: '',
  authToken: '',
};


function currentUser(state = initUserState, action) {
  switch (action.type) {
    case INIT_USER:
      return {
        ...state,
        sid: action.sid,
        authToken: action.authToken
      };
      break;
    default:
      return state;
  }
}

export default combineReducers({
  currentUser,
});
