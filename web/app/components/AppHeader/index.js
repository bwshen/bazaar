import React from 'react';
import PropTypes from 'prop-types';
import { withStyles } from '@material-ui/core/styles';
import AppBar from '@material-ui/core/AppBar';
import Toolbar from '@material-ui/core/Toolbar';
import Typography from '@material-ui/core/Typography';
import Button from '@material-ui/core/Button';
import IconButton from '@material-ui/core/IconButton';
import MenuIcon from '@material-ui/icons/Menu';
import LoginDialog from 'components/LoginDialog';
import axios from 'axios';
import Link from "react-router-dom/es/Link";

const styles = {
  root: {
    flexGrow: 1,
  },
  flex: {
    flex: 1,
  },
  menuButton: {
    marginLeft: -12,
    marginRight: 20,
  },
};

class ButtonAppBar extends React.Component {
  constructor() {
    super();
  }

  getApiOrder = () => {
    // axios.get('http://localhost:4000/api/orders/v8a3qw-jqg5vda/?format=json', { withCredentials: true });
    axios.post('http://localhost:4000/api/order_updates/', {
      time_limit_delta: 7200,
      order_sid: 'v8a3qw-jqg5vda',
    }, {
      headers: { 'X-CSRFTOKEN': this._getCookie('csrftoken') },
    });
  }

  _getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie != '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();

      // Does this cookie string begin with the name we want?
        if (cookie.substring(0, name.length + 1) == (`${name}=`)) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }


  render() {
    const { classes } = this.props;
    return (
      <div className={classes.root}>
        <AppBar position="static" >
          <Toolbar>
            <IconButton
              className={classes.menuButton}
              color="inherit"
              aria-label="Menu"
            >
              <MenuIcon />
            </IconButton>
            <Typography
              variant="title"
              color="inherit"
              className={classes.flex}
            >
      <Link to={"/"}>
        Bodega Web Services
      </Link>
      </Typography>
            <Button color="inherit" onClick={this.getApiOrder}>getApiOrder</Button>
            <LoginDialog />
          </Toolbar>
        </AppBar>
      </div>
    );
  }
}

ButtonAppBar.propTypes = {
  classes: PropTypes.object.isRequired,
};

export default withStyles(styles)(ButtonAppBar);
