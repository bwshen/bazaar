import React from 'react';
import PropTypes from 'prop-types';
import { Helmet } from 'react-helmet';
import { connect } from 'react-redux';

import Section from './Section';
import {API} from 'utils/api';
import {HOST} from '../../constants/conf';
import H2 from "../../components/H2";
import H3 from "../../components/H3";
import OrderProgess from 'components/OrderProgress';

class OrderPage extends React.Component {
  state = {
    order: null,
  };

  componentWillMount() {
    API.get(HOST + '/api/orders/' + this.props.match.params.orderSid)
      .then((response) => {
        this.setState({
          order: response.data,
        });
      });
  }

  render() {
    if (this.state.order) {
      let thething;
      for (let item in this.state.order.items_json) {
        if (this.state.order.items_json[item]) {
          thething = this.state.order.items_json[item];
          break;
        }
      }

      const m = new Date(this.state.order.time_created);
      const dateString = m.getUTCHours() + ":" + m.getUTCMinutes() + ":" + m.getUTCSeconds() + " " + m.getUTCFullYear() +"/"+ (m.getUTCMonth()+1) +"/"+ m.getUTCDate();
     
      let fulfilledItem;
      if (this.state.order.status === 'FULFILLED' && this.state.order.fulfilled_items) {
        for (let item in this.state.order.fulfilled_items) {
          if (this.state.order.fulfilled_items[item]) {
            fulfilledItem = this.state.order.fulfilled_items[item];
            break;
          }
        }
       console.log(fulfilledItem);
      }
      return (
        <article>
          <Helmet>
            <title>Home Page</title>
            <meta name="description" content="A React.js Boilerplate application homepage" />
          </Helmet>
          <div>
            <H2>
              Order {this.state.order.sid}
            </H2>
            <H3>
              Status: {this.state.order.status}
            </H3>
            {fulfilledItem && fulfilledItem.platform.startsWith('DYNAPOD') && <H3>
              <a href={"ftp://files-master.colo.rubrik-lab.com/Dynapod/"+fulfilledItem.filename.replace('.yml','')+"/"+fulfilledItem.filename}>YML File</a>
            </H3>
            }
            <H3>
              Time created: {dateString}
            </H3>
            <Section>
              {`Item platform is ${thething.requirements.platform} at location ${thething.requirements.location}`}
            </Section>
            {this.state.order.status === 'OPEN' && <OrderProgess sid={this.state.order.sid}/>}
          </div>
        </article>
      );
    }

    return (
      <article>
        <Helmet>
          <title>Home Page</title>
          <meta name="description" content="A React.js Boilerplate application homepage" />
        </Helmet>
        <div>
          <Section>
            {`Fetching info on order ${this.props.match.params.orderSid}...`}
          </Section>
        </div>
      </article>
    );
  }
}

OrderPage.propTypes = {
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

export default connect(mapStateToProps, mapDispatchToProps)(OrderPage);
