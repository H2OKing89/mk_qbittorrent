import {StyleSheet} from 'react-native';
import {responsiveFont} from '../../../Util';
const styles = StyleSheet.create({
  container: {
    padding: 15,
  },
  rowItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  badgeContainer: {
    backgroundColor: 'red',
    position: 'absolute',
    right: 0,
    borderRadius: 30,
    width: 15,
    height: 15,
    justifyContent: 'center',
    alignItems: 'center',
  },
  badgeFont: {color: '#fff', fontSize: responsiveFont(9)},
});

export default styles;
