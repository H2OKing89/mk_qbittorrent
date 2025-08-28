import React, {useState, useEffect} from 'react';
import {View, Text, FlatList, Image, Dimensions} from 'react-native';
import styles from './styles';
import {Promo} from '@data';
import {Card} from 'react-native-shadow-cards';
import Ripple from 'react-native-material-ripple';
import {useNavigation} from '@react-navigation/native';
import ToastCustom from '../../../lib/ToastCustom';

const Product = (props) => {
  const navigation = useNavigation();
  const [menu, setMenu] = useState(Promo);
  useEffect(() => {
    setMenu(Promo);
  }, []);
  const onPressDetail = (item) => {
    navigation.navigate('DetailScreen', {item});
  };
  const onPressMore = () => {
    navigation.navigate('FeedScreen');
  };
  const renderItem = ({item}) => {
    return (
      <View>
        <Card style={styles.item}>
          <Image
            source={item.image}
            // resizeMode={'contain'}
            style={styles.sliderItems}
          />
          <View style={styles.itemPrice}>
            <Ripple
              rippleOpacity={0}
              onPress={() => {
                ToastCustom.show(`added ${item.label}`, ToastCustom.SHORT);
                props.onPress();
              }}
              style={styles.rowTitle}>
              <Image source={require('@images/plus.png')} style={styles.icon} />

              <Text style={styles.font}>{item.label}</Text>
            </Ripple>
          </View>
        </Card>
      </View>
    );
  };
  const keyExtractor = (item, index) => {
    return index.toString();
  };

  return (
    <View style={styles.container}>
      <View style={styles.rowTitle}>
        <Text style={styles.title}>{props.title}</Text>
      </View>
      <FlatList
        keyExtractor={keyExtractor}
        horizontal
        snapToAlignment={'start'}
        snapToInterval={Dimensions.get('window').width * 0.5}
        data={menu}
        renderItem={renderItem}
        showsHorizontalScrollIndicator={false}
      />
    </View>
  );
};

export default Product;
