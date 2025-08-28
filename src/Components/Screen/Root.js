import React from 'react';
import {createStackNavigator} from '@react-navigation/stack';
import BottomTab from '@components/Modules/BottomTab';

const Stack = createStackNavigator();
const Root = () => {
  return (
    <Stack.Navigator>
      <Stack.Screen
        name="HomeRoot"
        options={{
          headerShown: false,
          cardStyle: {
            backgroundColor: '#fff',
          },
        }}
        component={BottomTab}
      />
    </Stack.Navigator>
  );
};

export default Root;
