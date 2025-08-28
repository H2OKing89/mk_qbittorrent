import {Dimensions, StyleSheet} from 'react-native';
import {responsiveFont} from '../../../Util';
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  title: {
    color: '#000',
    fontSize: responsiveFont(18),
    fontWeight: 'bold',
    marginLeft: 20,
  },
  coloredContainer: {
    flex: 1,
    backgroundColor: '#F2F2F2',
    borderTopRightRadius: Dimensions.get('window').height * 0.3,
  },
  scrollContainer: {
    backgroundColor: '#fff',
  },
  position: {
    position: 'absolute',
    flex: 1,
    top: 0,
    bottom: 0,
    left: 0,
    right: 0,
  },
});

export default styles;
