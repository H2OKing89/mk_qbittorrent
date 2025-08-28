import React, {useState} from 'react';
import {View, Text, StatusBar} from 'react-native';
import BurgerMenu from '../BurgerMenu';
import styles from './styles';
import Icon from 'react-native-vector-icons/Entypo';

const Header = (props) => {
  const [active, setToogle] = useState(false);
  const setToogleActive = () => {
    setToogle(!active);
  };
  return (
    <View style={styles.container}>
      <StatusBar barStyle={'dark-content'} backgroundColor="#fff" />
      <View style={styles.rowItem}>
        <BurgerMenu
          type="spinCross"
          active={active}
          onPress={setToogleActive}
        />
        <View>
          <Icon name="shopping-cart" size={30} color="#000" />
          {props.badgeCount > 0 && (
            <View style={styles.badgeContainer}>
              <Text style={styles.badgeFont}>{props.badgeCount}</Text>
            </View>
          )}
        </View>
      </View>
    </View>
  );
};

export default Header;
