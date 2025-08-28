import React, {useState} from 'react';
import {View} from 'react-native';
import styles from './styles';
import {Text} from 'react-native';
import Carousel from '@components/Modules/Carousel';
import Preview from '@components/Modules/Carousel/Preview';
import Product from '@components/Modules/Product';
import {CarouselImages} from '@data';
import Header from '@components/Modules/Header';
import {ScrollView} from 'react-native-gesture-handler';

const HomeScreen = () => {
  const [count, setBadgeCount] = useState(0);
  return (
    <View style={styles.container}>
      <View style={styles.coloredContainer}>
        <Header badgeCount={count} />
        <Text style={styles.title}>Nike App Store</Text>
        <ScrollView>
          <Carousel
            data={CarouselImages}
            width={275}
            timer={5000}
            component={<Preview />}
            onPress={(item) => alert(JSON.stringify(item))}
            contentContainerStyle={{paddingHorizontal: 16}}
            indicatorActiveColor={'#000'}
            animation
            local
          />
          <Product onPress={() => setBadgeCount(count + 1)} />
        </ScrollView>
      </View>
    </View>
  );
};
HomeScreen.navigationOptions = {
  title: 'Home',
};

export default HomeScreen;
