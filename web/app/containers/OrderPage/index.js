import React from 'react';
import PropTypes from 'prop-types';
import { Helmet } from 'react-helmet';
import { connect } from 'react-redux';

import Section from './Section';

export class OrderPage extends React.Component {
  render() {
    return (
      <article>
        <Helmet>
          <title>Home Page</title>
          <meta name="description" content="A React.js Boilerplate application homepage" />
        </Helmet>
        <div>
          <Section>
            {`This is order ${this.props.orderSid}!!!!`}
          </Section>
        </div>
      </article>
    );
  }
}

OrderPage.propTypes = {
  orderSid: PropTypes.string,
  currentUser: PropTypes.object,
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
