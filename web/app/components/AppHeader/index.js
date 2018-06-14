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
import Link from "react-router-dom/es/Link";
import {withRouter} from 'react-router-dom';

const styles = {
  root: {
    flexGrow: 0,
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
  constructor(props) {
    super(props);
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
            {this.props.location.pathname !== '/create' && <Button variant="outlined" color="inherit" component={({...props}) => <Link to='/create' {...props} />}>Create an Order</Button>}
            <LoginDialog />
          </Toolbar>
        </AppBar>
      </div>
    );
  }
}

ButtonAppBar.propTypes = {
  classes: PropTypes.object.isRequired,
  match: PropTypes.object,
};

export default withRouter(withStyles(styles)(ButtonAppBar));
