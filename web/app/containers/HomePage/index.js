/*
 * HomePage
 *
 * This is the first thing users see of our App, at the '/' route
 */

import React from 'react';
import PropTypes from 'prop-types';
import { Helmet } from 'react-helmet';
import { connect } from 'react-redux';
import { compose } from 'redux';
import { createStructuredSelector } from 'reselect';

import injectReducer from 'utils/injectReducer';
import injectSaga from 'utils/injectSaga';
import { makeSelectRepos, makeSelectLoading, makeSelectError } from 'containers/App/selectors';
import Section from './Section';
import { loadRepos } from '../App/actions';
import { changeUsername } from './actions';
import reducer from './reducer';
import saga from './saga';
import OrderList from "../../components/OrderList";
import axios from 'axios';
import {HOST} from '../../constants/conf';
import HomeLink from "./HomeLink";

export class HomePage extends React.PureComponent { // eslint-disable-line react/prefer-stateless-function
  state = {
    orderList: []
  };

  componentWillMount() {
    this.updateListWithCurrentUser();
  }

  componentWillUpdate(nextProps, nextState) {
    const { sid } = nextProps.currentUser;
    if (sid !== this.props.currentUser.sid) {
      this.updateList(sid);
    }
  }

  updateListWithCurrentUser() {
    const { sid}  = this.props.currentUser;
    if (sid === '') return;
    this.updateList(sid);
  }

  updateList(sid) {
    axios
      .get(HOST + `/api/orders/?format=json&owner_sid=${sid}&status_live=True`)
      .then((response) => {
      this.setState({
      orderList: response.data.results,
    });
  });
  }

  render() {
    return (
      <article>
        <Helmet>
          <title>Home Page</title>
          <meta name="description" content="" />
        </Helmet>
        <div>
          <Section>
            <OrderList orderList={this.state.orderList} actionCallback={this.updateListWithCurrentUser.bind(this)} />
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
};

export function mapDispatchToProps(dispatch) {
  return {};
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
