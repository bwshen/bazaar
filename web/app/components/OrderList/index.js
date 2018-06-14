import React from 'react';
import PropTypes from 'prop-types';
import List from '@material-ui/core/List';
import ListItem from '@material-ui/core/ListItem';
import ListItemAvatar from '@material-ui/core/ListItemAvatar';
import ListItemSecondaryAction from '@material-ui/core/ListItemSecondaryAction';
import RestoreIcon from '@material-ui/icons/Restore';
import DeleteIcon from '@material-ui/icons/Delete';
import AssignmentTurnedInIcon from '@material-ui/icons/AssignmentTurnedIn';
import IconButton from '@material-ui/core/IconButton';
import Avatar from '@material-ui/core/Avatar';
import ListItemText from '@material-ui/core/ListItemText';
import WatchLaterIcon from '@material-ui/icons/WatchLater';
import Link from "react-router-dom/es/Link";
import axios from 'axios';
import {HOST} from 'constants/conf';
import { connect } from 'react-redux';
import Countdown from 'react-cntdwn'

const fullfilledStyle = {
  backgroundColor: 'green',
}

const openedStyle = {
  backgroundColor: 'orange',
}

const calcTimeLeft = function(timeLeft) {
  const firstPass = timeLeft.split(' ');
  const days = 1 in firstPass ? parseInt(firstPass[0], 10) : 0;
  const secondPass = firstPass[1 in firstPass ? 1 : 0].split(':');
  const hours = 0 in secondPass ? parseInt(secondPass[0], 10) : 0;
  const mins = 1 in secondPass ? parseInt(secondPass[1], 10) : 0;
  const secs = 2 in secondPass ? parseInt(secondPass[2], 10) : 0;
  const miliseconds =
    days * 24 * 60 * 60 * 1000 +
    hours * 60 * 60 * 1000 +
    mins * 60 * 1000 +
    secs *  1000;
  console.log(days, hours, mins, secs);
  return miliseconds;
}

class OrderList extends React.Component {

  extendOrder(order, e) {
    e.preventDefault();
    axios.post(HOST+"/api/order_updates/", {
      order_sid: order.sid,
      comment: 'Extending order using Bazaar',
      time_limit_delta: '1:00:00'
    }, {
      headers: { 'X-CSRFTOKEN': this._getCookie('csrftoken') },
      withCredentials: true,
    }).then(this.props.actionCallback);
  }

  closeOrder(order, e) {
    e.preventDefault();
    axios.post(HOST+"/api/order_updates/", {
      order_sid: order.sid,
      comment: 'Closing order through Bazaar',
      new_status: 'CLOSED'
    }, {
      headers: { 'X-CSRFTOKEN': this._getCookie('csrftoken') },
      withCredentials: true,
    }).then(this.props.actionCallback);
  }

  _getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length == 2) return parts.pop().split(';').shift();
  }

  orderToListItem(order) {
    const avatarStyle = order.status === 'FULFILLED' ? fullfilledStyle: order.status === 'OPEN' ? openedStyle: {};
    const timeLeft = order.time_limit
    return (
      <Link to={"/order/" + order.sid} key={order.sid} style={{ textDecoration: 'none' }}>
        <ListItem>
          <ListItemAvatar>
            <Avatar style={avatarStyle} >
             {order.status === 'FULFILLED' &&  <AssignmentTurnedInIcon/>}
              {order.status === 'OPEN' &&  <WatchLaterIcon/>}
            </Avatar>
          </ListItemAvatar>
          <ListItemText
            primary={order.sid}
            secondary={`Status: ${order.status}`}
          />
    {order.status === 'FULFILLED' && <div style={{flex: "1 1 auto"}}><Countdown
      targetDate={new Date(Date.now() + calcTimeLeft(order.time_limit))}
      interval={1000}
      format={{
        day: 'dd',
        hour: 'hh',
        minute: 'mm',
        second: 'ss'
    }}
      timeSeparator={':'}
      leadingZero
      /></div>}
          <ListItemSecondaryAction>
            {order.status === 'FULFILLED' && <IconButton aria-label="Extend" onClick={this.extendOrder.bind(this, order)}>
            <RestoreIcon />
            </IconButton>}
            <IconButton aria-label="Delete" onClick={this.closeOrder.bind(this, order)}>
              <DeleteIcon />
            </IconButton>
          </ListItemSecondaryAction>
        </ListItem>
      </Link>
    );
  }

  render() {
    return (
      <List>
        {this.props.orderList.map(this.orderToListItem.bind(this))}
      </List>
    );
  }
}

const mapStateToProps = (state) => {return {};};

export function mapDispatchToProps(dispatch) {
  return {
    dispatch,
  };
}

OrderList.propTypes = {
  orderList: PropTypes.arrayOf(PropTypes.object),
  actionCallback: PropTypes.func,
};

export default connect(mapStateToProps, mapDispatchToProps)(OrderList);
