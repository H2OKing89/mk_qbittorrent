import {StyleSheet, Dimensions} from 'react-native';
import {responsiveFont} from '@util';
const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  sliderItems: {
    height: Dimensions.get('window').height * 0.6,
    width: Dimensions.get('window').width,
  },
  position: {
    position: 'absolute',
    flex: 1,
    top: 0,
    bottom: 0,
    left: 0,
    right: 0,
  },
  title: {
    fontSize: responsiveFont(15),
    fontWeight: 'bold',
    marginBottom: 20,
  },
  fontTitle: {
    fontSize: responsiveFont(15),
    fontWeight: 'bold',
  },
});

export default styles;
