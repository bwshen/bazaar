import React from 'react';
import PropTypes from 'prop-types';
import { withStyles } from '@material-ui/core/styles';
import LinearProgress from '@material-ui/core/LinearProgress';

const styles = {
  root: {
    flexGrow: 1,
  },
};

const stuff = [
  'Consulting AI',
  'Optimizing combinatorials',
  'Waiting for a parking space',
  'Ignoring your order to deal with a customer issue',
  'Build is broken',
  'Searching the Attic',
  'Waiting for the testing pipeline',
  'Putting out a fire in the server room',
  'Walking over to Building 3 to use the restroom',
  'Pipe Broken, cannot find bodega',
  'Did you really think you would ever get a dynapod?',
];

function itIsMidnight(progress) {
  return stuff[Math.min(Math.floor(progress / 10), 10)];
}

class OrderProgress extends React.Component {
  state = {
    completed: 0,
  };

  componentDidMount() {
    this.timer = setInterval(this.progress, 500);
  }

  componentWillUnmount() {
    clearInterval(this.timer);
  }

  timer = null;

  progress = () => {
    const { completed } = this.state;
    if (completed === 100) {
      clearInterval(this.timer);
    } else {
      const diff = Math.random() * 2;
      this.setState({ completed: Math.min(completed + diff, 100) });
    }
  };

  render() {
    const { classes } = this.props;
    return (
      <div>
      <LinearProgress variant="determinate" value={this.state.completed} style={{height: '30px', borderRadius: '15px'}} />
      <p>{itIsMidnight(this.state.completed)}</p>
      </div>
    );
  }
}

OrderProgress.propTypes = {
  classes: PropTypes.object.isRequired,
};

export default withStyles(styles)(OrderProgress);
