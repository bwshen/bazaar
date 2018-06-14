/*
 * HomePage
 *
 * This is the first thing users see of our App, at the '/' route
 */

import React from 'react';
import PropTypes from 'prop-types';
import { Helmet } from 'react-helmet';
import { FormattedMessage } from 'react-intl';
import { connect } from 'react-redux';
import { compose } from 'redux';
import { createStructuredSelector } from 'reselect';

import injectReducer from 'utils/injectReducer';
import injectSaga from 'utils/injectSaga';
import { makeSelectRepos, makeSelectLoading, makeSelectError } from 'containers/App/selectors';
import H2 from 'components/H2';
import ReposList from 'components/ReposList';
import AtPrefix from './AtPrefix';
import CenteredSection from './CenteredSection';
import Form from './Form';
import Input from './Input';
import Section from './Section';
import messages from './messages';
import { loadRepos } from '../App/actions';
import { changeUsername } from './actions';
import { makeSelectUsername } from './selectors';
import reducer from './reducer';
import saga from './saga';
import OrderList from "../../components/OrderList";
import liveOrders from '../../constants/liveOrders';
import axios from 'axios';
import {HOST} from '../../constants/conf';
import HomeLink from "./HomeLink";

export class HomePage extends React.PureComponent { // eslint-disable-line react/prefer-stateless-function
  state = {
    orderList: []
  };

  componentWillMount() {
    const { sid } = this.props.currentUser;
    if (sid !== '') {
      // ask for current user order list
      axios.get(HOST + `/api/orders/?format=json&owner_sid=${sid}&status_live=True`)
        .then((response) => {
          console.log("LIVE ORDERS", response);
          this.setState({
            orderList: response.data.results,
          });
        });
    }
  }

  componentWillUpdate(nextProps, nextState) {
    const { sid } = nextProps.currentUser;
    if (sid !== '' && sid !== this.props.currentUser.sid) {
      // ask for current user order list
      axios.get(HOST + `/api/orders/?format=json&owner_sid=${sid}&status_live=True`)
        .then((response) => {
          console.log("LIVE ORDERS", response);
          this.setState({
            orderList: response.data.results,
          });
        });
    }
  }

  render() {
    return (
      <article>
        <Helmet>
          <title>Home Page</title>
          <meta name="description" content="A React.js Boilerplate application homepage" />
        </Helmet>
        <div>
          <Section>
            <HomeLink to={"/create"}>
              Create new order
            </HomeLink>
          </Section>
          <Section>
            <OrderList orderList={this.state.orderList} />
          </Section>
        </div>
      </article>
    );
  }
}

HomePage.propTypes = {
  loading: PropTypes.bool,
  error: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.bool,
  ]),
  repos: PropTypes.oneOfType([
    PropTypes.array,
    PropTypes.bool,
  ]),
  onSubmitForm: PropTypes.func,
  username: PropTypes.string,
  onChangeUsername: PropTypes.func,
};

export function mapDispatchToProps(dispatch) {
  return {
    onChangeUsername: (evt) => dispatch(changeUsername(evt.target.value)),
    onSubmitForm: (evt) => {
      if (evt !== undefined && evt.preventDefault) evt.preventDefault();
      dispatch(loadRepos());
    },
  };
}

const mapStateToProps = function(state) {
  const currentUser = state.get("global").get("currentUser");
  return {
    currentUser
  };
};

const withConnect = connect(mapStateToProps, mapDispatchToProps);

const withReducer = injectReducer({ key: 'home', reducer });
const withSaga = injectSaga({ key: 'home', saga });

export default compose(
  withReducer,
  withSaga,
  withConnect,
)(HomePage);
