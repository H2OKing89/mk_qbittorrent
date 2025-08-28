import {StyleSheet, Dimensions} from 'react-native';
const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  containerItem: {
    paddingVertical: 28,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'red',
    marginLeft: 20,
  },
  sliderItems: {
    width: Dimensions.get('window').width * 0.85,
    height: 155,
    borderRadius: 20,
    resizeMode: 'cover',
  },
  dot: {
    position: 'absolute',
  },
});

export default styles;
