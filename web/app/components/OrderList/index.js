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
import Link from "react-router-dom/es/Link";


class OrderList extends React.Component {
  orderToListItem(order) {
    return (
      <Link to={"/order/" + order.sid} key={order.sid}>
        <ListItem>
          <ListItemIcon>
            <WatchLaterIcon/>
          </ListItemIcon>
          <ListItemText
            primary={order.sid}
            secondary={`Status: ${order.status}`}
          />
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

OrderList.propTypes = {
  orderList: PropTypes.arrayOf(PropTypes.object),
};

export default OrderList;
