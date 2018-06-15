import React from 'react';
import PropTypes from 'prop-types';
import { connect } from 'react-redux';
import * as Recharts from 'recharts';

const {LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend} = Recharts;

class CustomTooltip extends React.Component {
  render() {
    const { active, payload, label } = this.props;
    if (active && payload) {
      return (
        <div className="custom-tooltip">
          <p className="label"><span style={{fontWeight: 'bold', color: '#8884d8'}}>{`${label}: `}</span><span style={{color: 'green'}}>{`$${parseFloat(payload[0].value).toFixed(2)}`}</span></p>
        </div>
      );
    }
    return null;
  }
};

CustomTooltip.propTypes = {
  type: PropTypes.string,
  payload: PropTypes.array,
  label: PropTypes.string,
};

export class CostChart extends React.Component {
  state = {
    data: []
  };

  render () {
    return (
      <LineChart width={600} height={300} data={this.props.data}
    margin={{top: 5, right: 30, left: 20, bottom: 5}}>
  <XAxis dataKey="name"/>
      <YAxis/>
      <CartesianGrid strokeDasharray="3 3"/>
      <Tooltip content={<CustomTooltip/>}/>
      <Legend />
      <Line type="monotone" dataKey="cost" stroke="#8884d8" activeDot={{r: 8}}/>
      </LineChart>
  );
  }
};

const mapStateToProps = (state) => {return {};};

export function mapDispatchToProps(dispatch) {
  return {
    dispatch,
  };
}

CostChart.propTypes = {
  data: PropTypes.array,
};

export default connect(mapStateToProps, mapDispatchToProps)(CostChart);
