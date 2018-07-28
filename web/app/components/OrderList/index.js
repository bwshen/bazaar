import React from 'react';
import PropTypes from 'prop-types';
import List from '@material-ui/core/List';
import ListItem from '@material-ui/core/ListItem';
import ListItemAvatar from '@material-ui/core/ListItemAvatar';
import ListItemSecondaryAction from '@material-ui/core/ListItemSecondaryAction';
import ContentCopyIcon from '@material-ui/icons/ContentCopy';
import RestoreIcon from '@material-ui/icons/Restore';
import DeleteIcon from '@material-ui/icons/Delete';
import AssignmentTurnedInIcon from '@material-ui/icons/AssignmentTurnedIn';
import IconButton from '@material-ui/core/IconButton';
import Avatar from '@material-ui/core/Avatar';
import ListItemText from '@material-ui/core/ListItemText';
import WatchLaterIcon from '@material-ui/icons/WatchLater';
import Tooltip from '@material-ui/core/Tooltip';
import Link from "react-router-dom/es/Link";
import {API} from 'utils/api';
import {HOST} from 'constants/conf';
import { connect } from 'react-redux';
import Countdown from 'react-cntdwn'
import H2 from "../H2";


const fullfilledStyle = {
  backgroundColor: 'green',
}

const openedStyle = {
  backgroundColor: 'orange',
}

function getRequirements(order) {
  for (let item in order.items_json) {
    if (order.items_json[item]) {
      const resp = [], reqs = order.items_json[item].requirements;
      for (let key in reqs){
        resp.push(`${key}: ${reqs[key]}`);
      }
      return resp.join("\n");
    }
    return "";
  }
}

 function milisecondsToTime(milisecs){
    var timeLeft = Math.floor(milisecs / 1000);
    var secs = timeLeft % 60;
    timeLeft = Math.floor(timeLeft / 60);
    var minutes = timeLeft % 60;
    timeLeft = Math.floor(timeLeft/ 60);
    var hours = timeLeft % 24;
    timeLeft = Math.floor(timeLeft / 24);
    var days = timeLeft;
    var resp = [];
    if (days) resp.push(days + ' ');
    if (days && !hours) resp.push('00:');
    if (!!hours) resp.push(('0' + hours).slice(-2)+':');
    if ((days || hours) && !minutes) resp.push('00:');
    if (!!minutes) resp.push(('0' + minutes).slice(-2)+':');
    if((days || hours || minutes) && ! secs) resp.push('00');
    if (!!secs) resp.push(('0' + secs).slice(-2));
    return resp.join(''); 
}

function select(element) {
    var selectedText;

    if (element.nodeName === 'SELECT') {
        element.focus();

        selectedText = element.value;
    }
    else if (element.nodeName === 'INPUT' || element.nodeName === 'TEXTAREA') {
        var isReadOnly = element.hasAttribute('readonly');

        if (!isReadOnly) {
            element.setAttribute('readonly', '');
        }

        element.select();
        element.setSelectionRange(0, element.value.length);

        if (!isReadOnly) {
            element.removeAttribute('readonly');
        }

        selectedText = element.value;
    }
    else {
        if (element.hasAttribute('contenteditable')) {
            element.focus();
        }

        var selection = window.getSelection();
        var range = document.createRange();

        range.selectNodeContents(element);
        selection.removeAllRanges();
        selection.addRange(range);

        selectedText = selection.toString();
    }

    return selectedText;
}

class OrderList extends React.Component {

  extendOrder(order, e) {
    e.preventDefault();
    API.post(HOST+"/api/order_updates/", {
      order_sid: order.sid,
      comment: 'Extending order using Bazaar',
      time_limit_delta: milisecondsToTime((new Date()).setDate((new Date()).getDate() + 2) - new Date(order.ejection_time))
    }).then(this.props.actionCallback);
  }

  closeOrder(order, e) {
    e.preventDefault();
    API.post(HOST+"/api/order_updates/", {
      order_sid: order.sid,
      comment: 'Closing order through Bazaar',
      new_status: 'CLOSED'
    }).then(this.props.actionCallback);
  }

  copyConsumeOrder(order , e) {
    e.preventDefault();
    const isRTL = document.documentElement.getAttribute('dir') == 'rtl';
    const fakeElem = document.createElement('textarea');
    // Prevent zooming on iOS
    fakeElem.style.fontSize = '12pt';
    // Reset box model
    fakeElem.style.border = '0';
    fakeElem.style.padding = '0';
    fakeElem.style.margin = '0';
    // Move element out of screen horizontally
    fakeElem.style.position = 'absolute';
    fakeElem.style[ isRTL ? 'right' : 'left' ] = '-9999px';
    // Move element to the same position vertically
    let yPosition = window.pageYOffset || document.documentElement.scrollTop;
    fakeElem.style.top = `${yPosition}px`;

    fakeElem.setAttribute('readonly', '');
    fakeElem.value = 'lab/bin/bodega consume order '+order.sid;

    document.body.appendChild(fakeElem);
    const selectedText = select(fakeElem);
    try {
      document.execCommand('copy');
    } catch (err) {console.log(err);}
    document.body.removeChild(fakeElem);
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
        <ListItem button={true}>
          <Tooltip title={getRequirements(order)} PopperProps={{style: {whiteSpace: 'pre-line'}}}>
            <ListItemAvatar>
              <Avatar style={avatarStyle} >
               {order.status === 'FULFILLED' &&  <AssignmentTurnedInIcon/>}
                {order.status === 'OPEN' &&  <WatchLaterIcon/>}
              </Avatar>
            </ListItemAvatar>
          </Tooltip>
          <ListItemText
            primary={order.sid}
            secondary={`Status: ${order.status}`}
          />
    {order.status === 'FULFILLED' && <div style={{flex: "1 1 auto", paddingRight: '60px'}}><Countdown
      targetDate={new Date(order.ejection_time)}
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
            {
              order.status === 'FULFILLED' &&
              <Tooltip title={"Copy Consume Command"}>
                <IconButton aria-label="Copy Consume Command" onClick={this.copyConsumeOrder.bind(this, order)}>
                  <ContentCopyIcon />
                </IconButton>
              </Tooltip>
            }
            {
              order.status === 'FULFILLED' &&
              <Tooltip title={"Extend"}>
                <IconButton aria-label="Extend" onClick={this.extendOrder.bind(this, order)}>
                  <RestoreIcon />
                </IconButton>
              </Tooltip>
            }
            <Tooltip title={"Delete"}>
              <IconButton aria-label="Delete" onClick={this.closeOrder.bind(this, order)}>
                <DeleteIcon />
              </IconButton>
            </Tooltip>
          </ListItemSecondaryAction>
        </ListItem>
      </Link>
    );
  }

  render() {
    return (
      <div>
        <H2>
          All Orders
        </H2>
        <List>
          {this.props.orderList.map(this.orderToListItem.bind(this))}
        </List>
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

OrderList.propTypes = {
  orderList: PropTypes.arrayOf(PropTypes.object),
  actionCallback: PropTypes.func,
};

export default connect(mapStateToProps, mapDispatchToProps)(OrderList);
