import React from 'react';
import PropTypes from 'prop-types';
import List from '@material-ui/core/List';
import ListItem from '@material-ui/core/ListItem';
import ListItemText from '@material-ui/core/ListItemText';
import ListItemIcon from '@material-ui/core/ListItemIcon';
import WatchLaterIcon from '@material-ui/icons/WatchLater';
import Typography from '@material-ui/core/Typography';
import Button from '@material-ui/core/Button';
import IconButton from '@material-ui/core/IconButton';


class OrderList extends React.Component {
  orderToListItem(order) {
    return (
      <ListItem key={order.sid}>
        <ListItemIcon>
          <WatchLaterIcon/>
        </ListItemIcon>
        <ListItemText
          primary={order.sid}
          secondary={`Status: ${order.status}`}
        />
      </ListItem>
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

OrderList.propTypes = {
  orderList: PropTypes.arrayOf(PropTypes.object),
};

export default OrderList;