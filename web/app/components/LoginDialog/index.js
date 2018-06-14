import React from 'react';
import Button from '@material-ui/core/Button';
import TextField from '@material-ui/core/TextField';
import Dialog from '@material-ui/core/Dialog';
import DialogActions from '@material-ui/core/DialogActions';
import DialogContent from '@material-ui/core/DialogContent';
import DialogContentText from '@material-ui/core/DialogContentText';
import DialogTitle from '@material-ui/core/DialogTitle';
import {fetchUserIfExists} from "../../containers/App/actions";
import {connect} from "react-redux";
import {createSelector} from "reselect";

class LoginDialog extends React.Component {
  state = {
    open: false,
    loggedIn: !!this._getCookie('authtoken'),
    authtoken: '',
  };

  _getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length == 2) return parts.pop().split(';').shift();
  }

  open = () => {
    this.setState({ open: true, authtoken: ''});
  };

  close = () => {
    this.setState({ open: false, authtoken: '' });
  };

  login = () => {
    document.cookie = `authtoken=${this.state.authtoken};`;
    this.setState({ loggedIn: !!this._getCookie('authtoken') });

    this.props.dispatch(fetchUserIfExists());

    this.close();
  }

  setBodegaAuthToken = (e) => {
    this.setState({ authtoken: e.target.value });
  }


  logout = () => {
    document.cookie = 'sessionid=; expires=Thu, 01 Jan 1970 00:00:01 GMT;';
    document.cookie = 'csrftoken=; expires=Thu, 01 Jan 1970 00:00:01 GMT;';
    document.cookie = 'authtoken=; expires=Thu, 01 Jan 1970 00:00:01 GMT;';
    this.setState({ loggedIn: !!this._getCookie('authtoken') });
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
        Copy your Token from Bodega here:
      </DialogContentText>
            <TextField
              autoFocus
              margin="dense"
              id="authToken"
              label="BodegaAuthToken"
              type="text"
              onChange={this.setBodegaAuthToken}
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
