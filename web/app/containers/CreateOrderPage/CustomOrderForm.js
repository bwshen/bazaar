import React from 'react';
import PropTypes from 'prop-types';
import { withStyles } from '@material-ui/core/styles';
import Input from '@material-ui/core/Input';
import InputLabel from '@material-ui/core/InputLabel';
import FormHelperText from '@material-ui/core/FormHelperText';
import FormGroup from '@material-ui/core/FormGroup';
import FormLabel from '@material-ui/core/FormLabel';
import FormControl from '@material-ui/core/FormControl';
import FormControlLabel from '@material-ui/core/FormControlLabel';
import Select from '@material-ui/core/Select';
import NativeSelect from '@material-ui/core/NativeSelect';
import Checkbox from '@material-ui/core/Checkbox';
import Button from '@material-ui/core/Button';




const LOCATIONS = ['COLO', 'HQ'];
const PLATFORMS = ['DYNAPOD', 'DYNAPOD_ROBO', 'DYNAPOD_ROBO_HYPERV', 'PROD_BRIK']
const FLAGS = [
  'acropolis',
  'benchmarking',
  'encrypted',
  'esx_6_0',
  'fc_aix_agent',
  'fc_linux_agent',
  'hyperv_2016',
  'linux_agent',
  'linux_agent_all_versions',
  'manufacturable',
  'model_r6xx',
  'mssql',
  'robofm',
  'robossd',
  'stronger',
  'tpm',
  'windows_app_test_only',
];

const styles = theme => ({
  root: {
    display: 'flex',
    flexWrap: 'wrap',
  },
  formControl: {
    margin: theme.spacing.unit,
    minWidth: 120,
  },
  selectEmpty: {
    marginTop: theme.spacing.unit * 2,
  },
});

class CustomOrderForm extends React.Component {
  state = {
    location: LOCATIONS[0],
    platform: PLATFORMS[0],
    flags: FLAGS.reduce((acc, flag) => { return {...acc, [flag]: false}; }, {}),
  };

  handleChange = name => event => {
    this.setState({[name]: event.target.value});
  };

  handleFlagChange = name => event => {
    this.setState({
      flags: {
        ...this.state.flags,
        [name]: !this.state.flags[name],
      },
    });
  };

  render() {
    const { classes } = this.props;
    return (
      <div>
        <form autoComplete={"off"}>
          <FormControl className={classes.formControl}>
            <InputLabel htmlFor={'location'}>Location</InputLabel>
            <Select
              native
              value={this.state.location}
              onChange={this.handleChange('location')}
              inputProps={{
                name: 'location',
                id: 'location',
              }}>
              {LOCATIONS.map((loc) => {
                return (
                  <option value={loc} key={loc}>{loc}</option>
                );
              })}
            </Select>
          </FormControl>
          <FormControl className={classes.formControl}>
            <InputLabel htmlFor={'platform'}>Platform</InputLabel>
            <Select
              native
              value={this.state.platform}
              onChange={this.handleChange('platform')}
              inputProps={{
                name: 'platform',
                id: 'platform',
              }}>
              {PLATFORMS.map((platform) => {
                return (
                  <option value={platform} key={platform}>{platform}</option>
                );
              })}
            </Select>
          </FormControl>
          <div>
            <Button variant="contained" color="primary" onClick={() => {this.props.onSubmit(this.state);}}>
              Place Custom Order
            </Button>
          </div>
        </form>
      </div>
    );
  }
}

CustomOrderForm.propTypes = {
  classes: PropTypes.object.isRequired,
  onSubmit: PropTypes.func.isRequired,
};

export default withStyles(styles)(CustomOrderForm);
