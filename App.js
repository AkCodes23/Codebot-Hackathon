import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import Weather from './app/screens//Weather';
import Reminders from './app/screens/Reminders';
import FarmDatabase from './app/screens/FarmDatabase';
import AnimalRecordsScreen from './app/screens/AnimalRecordsScreen';
import Home from './app/screens/Home';
import GovtScheme from './app/screens/GovtScheme';
import VoiceAssistant from './app/screens/VoiceAssistant';
import LanguageScreen from './app/screens/LanguageScreen';
import WelcomeScreen from './app/screens/WelcomeScreen';
import Help from './app/screens/Help';
import CropAdvice from './app/screens/CropAdvice';
import Market from './app/screens/Market';
import Community from './app/screens/Community';


const Stack = createStackNavigator();

export default function App() {
  return (
    <NavigationContainer>
      <Stack.Navigator initialRouteName="LanguageScreen" screenOptions={{ headerShown: false }}>
        <Stack.Screen name="LanguageScreen" component={LanguageScreen} />
        <Stack.Screen name="WelcomeScreen" component={WelcomeScreen} />
        <Stack.Screen name="Home" component={Home} />
        <Stack.Screen name="Weather" component={Weather} />
        <Stack.Screen name="Reminders" component={Reminders} />        
        <Stack.Screen name="FarmDatabase" component={FarmDatabase} /> 
        <Stack.Screen name="AnimalRecordsScreen" component={AnimalRecordsScreen} />
        <Stack.Screen name="GovtScheme" component={GovtScheme} />
        <Stack.Screen name="VoiceAssistant" component={VoiceAssistant} />
        <Stack.Screen name="Help" component={Help} />
        <Stack.Screen name="CropAdvice" component={CropAdvice} />
        <Stack.Screen name="Market" component={Market} />
        <Stack.Screen name="Community" component={Community} />
       
      </Stack.Navigator>
    </NavigationContainer>
  );
}
