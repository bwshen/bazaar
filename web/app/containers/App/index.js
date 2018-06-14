/**
 *
 * App
 *
 * This component is the skeleton around the actual pages, and should only
 * contain code that should be seen on all pages. (e.g. navigation bar)
 */

import React from 'react';
import { Helmet } from 'react-helmet';
import styled from 'styled-components';
import {Switch, Route, withRouter} from 'react-router-dom';

import HomePage from 'containers/HomePage/Loadable';
import FeaturePage from 'containers/FeaturePage/Loadable';
import NotFoundPage from 'containers/NotFoundPage/Loadable';
import AppHeader from 'components/AppHeader';
import Footer from 'components/Footer';
import {fetchUserIfExists} from "./actions";
import {connect} from "react-redux";
import OrderPage from "../OrderPage";
import CreateOrderPage from "../CreateOrderPage";

const AppWrapper = styled.div`
  margin: 0 auto;
  display: flex;
  min-height: 100%;
  padding: 0;
  flex-direction: column;
`;

const AppBody = styled.div`
  max-width: calc(768px + 16px * 2);
  margin: 0 auto;
  display: flex;
  min-height: 100%;
  padding: 0 16px;
  flex-direction: column;
`;

class App extends React.Component {
  componentWillMount() {
    this.props.dispatch(fetchUserIfExists());
  }
  render() {
    return (
      <AppWrapper>
        <Helmet
          titleTemplate="%s - React.js Boilerplate"
          defaultTitle="React.js Boilerplate"
        >
          <meta name="description" content="A React.js Boilerplate application" />
        </Helmet>
        <AppHeader />
        <AppBody>
          <Switch>
            <Route exact path="/" component={HomePage} />
            <Route path="/order/:orderSid" component={OrderPage} />
            <Route path="/create" component={CreateOrderPage} />
            <Route path="" component={NotFoundPage} />
          </Switch>
        </AppBody>
      </AppWrapper>
    );
  }
}

const mapStateToProps = (state) => {return {};};

export function mapDispatchToProps(dispatch) {
  return {
    dispatch,
  };
}

export default withRouter(connect(mapStateToProps, mapDispatchToProps)(App));
