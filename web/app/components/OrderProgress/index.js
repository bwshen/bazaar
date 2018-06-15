import React from 'react';
import PropTypes from 'prop-types';
import { withStyles } from '@material-ui/core/styles';
import LinearProgress from '@material-ui/core/LinearProgress';

import axios from 'axios';
import {API} from 'utils/api';
import {HOST} from '../../constants/conf';

const styles = {
  root: {
    flexGrow: 1,
  },
};

class OrderProgress extends React.Component {
  state = {
		time: new Date()
  };

  componentDidMount() {
    this.timer = setInterval(this.progress, 10000);
		axios.get(HOST + '/order_times/' + this.props.sid).then((response) => {
			console.log(response.data.target_time);
			this.setState({time: Date.parse(response.data.target_time)})
		})
  }

  componentWillUnmount() {
    clearInterval(this.timer);
  }

  timer = null;

  progress = () => {
		console.log("TEST")
		console.log(this.props.sid)
		axios.get(HOST + '/order_times/' + this.props.sid).then((response) => {
			console.log(response.data.target_time);
			this.setState({time: Date.parse(response.data.target_time)})
		})
  };

  render() {
		console.log(this.state.time)
    const { classes } = this.props;
		let timeDiff = this.state.time - new Date();
		var line = ""

		if (timeDiff < 0) {
			timeDiff = 10000000;
			line = "Almost there!\n" + "Estimated Time: " + new Date(this.state.time);
		}
		else {
			timeDiff = 10000000 - timeDiff;
			if (timeDiff < 0) timeDiff = 0;
			console.log("TIME");
			console.log(this.state.time);
			console.log(this.state.time.toString());
				
			line = "Estimated Time: " + new Date(this.state.time);
		}

    return (
      <div>
      <LinearProgress variant="determinate" value={timeDiff/10000} style={{height: '30px', borderRadius: '15px'}} />
      <p>{line}</p>
      </div>
    );
  }
}

OrderProgress.propTypes = {
  classes: PropTypes.object.isRequired,
};

export default withStyles(styles)(OrderProgress);
