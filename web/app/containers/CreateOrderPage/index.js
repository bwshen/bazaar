import React from 'react';
import PropTypes from 'prop-types';
import { Helmet } from 'react-helmet';
import { connect } from 'react-redux';
import SettingsSystemDaydreamIcon from '@material-ui/icons/SettingsSystemDaydream'

import Section from './Section';
import List from '@material-ui/core/List';
import ListItem from '@material-ui/core/ListItem';
import ListItemText from '@material-ui/core/ListItemText';
import ListItemIcon from '@material-ui/core/ListItemIcon';
import H2 from "../../components/H2";

import axios from 'axios';
import {HOST} from '../../constants/conf';

class CreateOrderPage extends React.Component {
  createOrder(platform) {
    const orderParams = {
      "_item_1": {
        "requirements": {
          "location": "COLO",
          "network": "native",
          "platform": "DYNAPOD",
        },
        "type": "rktest_yml",
      },
    };
    axios.post(HOST + '/api/orders/', {
      items: JSON.stringify(orderParams),
    }, {
      headers: { 'X-CSRFTOKEN': this._getCookie('csrftoken') },
    }).then((response) => {
        console.log(response);
    }).catch((err) => {
      console.error("Failed to place order", err);
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
    return (
      <article>
        <Helmet>
          <title>Home Page</title>
          <meta name="description" content="A React.js Boilerplate application homepage" />
        </Helmet>
        <div>
          <H2>
            Select a preset from the list below.
          </H2>
          <Section>
            <List>
              <ListItem onClick={() => { this.createOrder("DYNAPOD"); }} button={true}>
                <ListItemIcon>
                  <SettingsSystemDaydreamIcon/>
                </ListItemIcon>
                <ListItemText primary={"DYNAPOD"} secondary={"COLO"} />
              </ListItem>
              <ListItem onClick={() => { this.createOrder("DYNAPOD_ROBO"); }} button={true}>
                <ListItemIcon>
                  <SettingsSystemDaydreamIcon/>
                </ListItemIcon>
                <ListItemText primary={"DYNAPOD_ROBO"} secondary={"COLO"} />
              </ListItem>
              <ListItem onClick={() => { this.createOrder("PROD_BRIK"); }} button={true}>
                <ListItemIcon>
                  <SettingsSystemDaydreamIcon/>
                </ListItemIcon>
                <ListItemText primary={"PROD_BRIK"} secondary={"COLO"} />
              </ListItem>
            </List>
          </Section>
        </div>
      </article>
    );
  }
}

CreateOrderPage.propTypes = {
  orderSid: PropTypes.string,
  currentUser: PropTypes.object,
  match: PropTypes.object,
};

export function mapDispatchToProps(dispatch) {
  return {
    dispatch,
  };
}

const mapStateToProps = function(state) {
  const currentUser = state.get("global").get("currentUser");
  return {
    currentUser
  };
}

export default connect(mapStateToProps, mapDispatchToProps)(CreateOrderPage);
