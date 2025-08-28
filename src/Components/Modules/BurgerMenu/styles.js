import {StyleSheet, Dimensions} from 'react-native';
import {responsiveFont, colorTheme} from '@util';
const WIDTH = Dimensions.get('window').width;
const styles = StyleSheet.create({
  container: {
    padding: 10,
  },
  font: {
    fontSize: responsiveFont(9.5),
  },
  fontGray: {
    fontSize: responsiveFont(9.5),
    color: '#ccc',
  },
  fontPercent: {
    fontSize: responsiveFont(9.5),
    color: '#f2000c',
    fontWeight: 'bold',
  },
  fontPrice: {
    fontSize: responsiveFont(12),
    fontWeight: 'bold',
  },
  fontFreeShipping: {
    fontSize: responsiveFont(11),
    fontWeight: 'bold',
    color: colorTheme.primaryColor,
    marginLeft: 10,
  },
  title: {
    fontSize: responsiveFont(15),
    fontWeight: 'bold',
    marginLeft: 10,
    marginBottom: 20,
  },
  titleGreen: {
    fontSize: responsiveFont(11),
    fontWeight: 'bold',
    color: colorTheme.primaryColor,
    marginLeft: 10,
    marginBottom: 20,
  },
  subtitle: {
    fontSize: responsiveFont(10),
    marginLeft: 10,
  },
  sliderItems: {
    width: WIDTH * 0.33,
    height: Dimensions.get('window').height * 0.18,
    borderTopLeftRadius: 6,
    borderTopRightRadius: 6,
  },
  item: {
    margin: 5,
    paddingBottom: 5,
    borderWidth: 0.5,
    borderColor: '#ccc',
    width: WIDTH * 0.33,
    borderRadius: 6,
    shadowColor: '#000',
    shadowOffset: {width: 0, height: 1},
    shadowOpacity: 0.2,
    shadowRadius: 2,
    elevation: 3,
  },
  itemPrice: {
    padding: 10,
  },
  row: {
    flexDirection: 'row',
    // alignItems: 'center',
  },
  rowTitle: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
    justifyContent: 'space-between',
  },
  percent: {
    padding: 5,
    backgroundColor: '#ffc4c7',
    borderRadius: 5,
    marginRight: 5,
  },
});

export default styles;
