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
import {API} from 'utils/api';
import {HOST} from '../../constants/conf';
import {CostChart} from 'components/costChart';
import CircularProgress from '@material-ui/core/CircularProgress';

const data = [
  {name: 'Page A', pv: 2400, amt: 2400},
  {name: 'Page B', pv: 1398, amt: 2210},
  {name: 'Page C', pv: 9800, amt: 2290},
  {name: 'Page D', pv: 3908, amt: 2000},
  {name: 'Page E', pv: 4800, amt: 2181},
  {name: 'Page F', pv: 3800, amt: 2500},
  {name: 'Page G', pv: 4300, amt: 2100},
];

const getMonth = (function(){
  const month = ['January', 'Febuary', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  return function(m) {
    return month[m < 0 ? 11 - m : m];
  }
})();

export class HomePage extends React.PureComponent { // eslint-disable-line react/prefer-stateless-function
  state = {
    orderList: [],
    costData: [],
  };

  componentWillMount() {
    this.updateListWithCurrentUser();
  }

  componentWillUpdate(nextProps, nextState) {
    const { sid } = nextProps.currentUser;
    if (sid !== this.props.currentUser.sid) {
      this.updateList(sid);
      this.getCost(sid);
    }
  }

  updateListWithCurrentUser() {
    const { sid}  = this.props.currentUser;
    if (sid === '') return;
    this.updateList(sid);
    this.getCost(sid);
  }

  updateList(sid) {
    API
      .get(HOST + `/api/orders/?format=json&owner_sid=${sid}&status_live=True`)
      .then((response) => {
        this.setState({
        orderList: response.data.results,
      });
    });
  }

  getCost(sid) {
    API.get(HOST + `monthly_cost/${sid}`).then((response) => {
      const now = new Date(Date.now());
      const data = JSON.parse(response.data.replace(',c',",'c").replace(/'/g, '"'));
      this.setState({
        costData: [
          {name: getMonth(now.getMonth() - 3), cost: data['cost_4thmonth']},
          {name: getMonth(now.getMonth() - 2), cost: data['cost_3rdmonth']},
          {name: getMonth(now.getMonth() - 1),cost: data['cost_2ndmonth']},
          {name: getMonth(now.getMonth()), cost: data['cost_1stmonth']},
        ]
      });
    });
  };

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
          <Section>
          <h2>Rubrik wants you to save money by closing orders</h2>
          <div style={{position: 'relative', margin: '0 auto'}}>
            {this.state.costData.length == 0 && <CircularProgress style={{position: 'absolute', top: 'calc(50% - 50px)', left: 'calc(50% - 25px)'}} size={50} />}
            <CostChart data={this.state.costData} />
          </div>
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
