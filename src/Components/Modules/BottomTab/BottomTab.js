import React from 'react';
import {BottomMenu} from '@data';
import {createBottomTabNavigator} from '@react-navigation/bottom-tabs';
import {Text, Image} from 'react-native';
import {responsiveFont, colorTheme} from '@util';

const Tab = createBottomTabNavigator();

const BottomTab = () => {
  return (
    <Tab.Navigator
      tabBarOptions={{
        style: {
          padding: 10,
          backgroundColor: '#F2F2F2',
          elevation: 0,
          borderWidth: 0,
        },
      }}>
      {BottomMenu.map((item) => (
        <Tab.Screen
          key={item.name}
          name={item.name}
          component={item.component}
          options={{
            tabBarLabel: ({color, size, focused}) => (
              <Text
                // eslint-disable-next-line react-native/no-inline-styles
                style={{
                  color: focused ? colorTheme.primaryColor : 'gray',
                  fontSize: responsiveFont(9),
                  marginBottom: 5,
                }}
              />
            ),
            tabBarIcon: ({color, size, focused}) => (
              <Image
                source={focused ? item.activeIcon : item.inActiveIcon}
                style={{width: 25, height: 25}}
                resizeMode="contain"
              />
            ),
          }}
        />
      ))}
    </Tab.Navigator>
  );
};
export default BottomTab;
