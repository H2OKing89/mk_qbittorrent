import {Dimensions, StyleSheet} from 'react-native';
import {responsiveFont} from '../../../Util';
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
    justifyContent: 'center',
    alignItems: 'center',
  },
  title: {
    color: '#000',
    fontSize: responsiveFont(18),
    fontWeight: 'bold',
  },
  coloredContainer: {
    flex: 1,
    backgroundColor: '#F2F2F2',
    borderTopRightRadius: Dimensions.get('window').height * 0.3,
  },
});

export default styles;
