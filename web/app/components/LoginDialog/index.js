import React from 'react';
import Button from '@material-ui/core/Button';
import TextField from '@material-ui/core/TextField';
import Dialog from '@material-ui/core/Dialog';
import DialogActions from '@material-ui/core/DialogActions';
import DialogContent from '@material-ui/core/DialogContent';
import DialogContentText from '@material-ui/core/DialogContentText';
import DialogTitle from '@material-ui/core/DialogTitle';
import axios from 'axios';
import {HOST} from "../../constants/conf";
import {initUser} from "../../containers/App/actions";
import {connect} from "react-redux";
import {createSelector} from "reselect";

class LoginDialog extends React.Component {
  state = {
    open: false,
    loggedIn: !!this._getCookie('sessionid'),
    sessionId: '',
    csrf: '',
  };

  _getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length == 2) return parts.pop().split(';').shift();
  }

  open = () => {
    this.setState({ open: true, sessionId: '', csrf: '' });
  };

  close = () => {
    this.setState({ open: false });
  };

  login = () => {
    document.cookie = `sessionid=${this.state.sessionId};`;
    document.cookie = `csrftoken=${this.state.csrf};`;
    this.setState({ loggedIn: !!this._getCookie('sessionid') });

    // hit profile endpoint, retrieve owner sid
    axios.get(HOST+"/api/profile/", {
      withCredentials: true,
    }).then((response) => {
      this.props.dispatch(initUser(response.data.sid, response.data.auth_token));
    });


    this.close();
  }

  setSessionId = (e) => {
    console.log(e.target.value);
    this.setState({ sessionId: e.target.value });
  }

  setCSRFToken = (e) => {
    this.setState({ csrf: e.target.value });
  }

  logout = () => {
    document.cookie = 'sessionid=; expires=Thu, 01 Jan 1970 00:00:01 GMT;';
    document.cookie = 'csrftoken=; expires=Thu, 01 Jan 1970 00:00:01 GMT;';
    this.setState({ loggedIn: !!this._getCookie('sessionid') });
  }

  render() {
    return (
      <div>
        {!this.state.loggedIn ? <Button color="inherit" onClick={this.open}>Login</Button> : <Button color="inherit" onClick={this.logout}>Logout</Button> }
        <Dialog
          open={this.state.open}
          onClose={this.close}
          aria-labelledby="form-dialog-title"
        >
          <DialogTitle id="form-dialog-title">Login</DialogTitle>
          <DialogContent>
            <DialogContentText>
        Copy your Tokens from Bodega here:
      </DialogContentText>
            <TextField
              autoFocus
              margin="dense"
              id="sessionId"
              label="Session Id"
              type="text"
              onChange={this.setSessionId}
              fullWidth
            />
            <TextField
              margin="dense"
              id="CSRFToken"
              label="Optional CSRF Token"
              type="text"
              onChange={this.setCSRFToken}
              fullWidth
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={this.close} color="secondary">Cancel</Button>
            <Button onClick={this.login} color="primary">Login</Button>
          </DialogActions>
        </Dialog>
      </div>
    );
  }
}

const mapStateToProps = (state) => {return {};};

export function mapDispatchToProps(dispatch) {
  return {
    dispatch,
  };
}

export default connect(mapStateToProps, mapDispatchToProps)(LoginDialog);
