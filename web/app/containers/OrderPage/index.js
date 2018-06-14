import React from 'react';
import PropTypes from 'prop-types';
import { Helmet } from 'react-helmet';
import { connect } from 'react-redux';

import Section from './Section';
import axios from 'axios';
import {HOST} from '../../constants/conf';
import H2 from "../../components/H2";
import H3 from "../../components/H3";

class OrderPage extends React.Component {
  state = {
    order: null,
  };

  componentWillMount() {
    axios.get(HOST + '/api/orders/' + this.props.match.params.orderSid)
      .then((response) => {
        this.setState({
          order: response.data,
        });
      });
  }

  render() {
    if (this.state.order) {
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
            <H3>
              Time created: {this.state.order.time_created}
            </H3>
            <Section>
              {`Item platform is ${this.state.order.items_json._item_1.requirements.platform} at location ${this.state.order.items_json._item_1.requirements.location}`}
            </Section>
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
