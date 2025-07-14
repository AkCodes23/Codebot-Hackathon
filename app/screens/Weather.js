import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  SafeAreaView,
  Modal,
  Pressable,
  Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import axios from 'axios';
import * as Location from 'expo-location';

const Weather = ({ navigation }) => {
  const [menuVisible, setMenuVisible] = useState(false);
  const [location, setLocation] = useState(null);
  const [city, setCity] = useState('Fetching...');
  const [weather, setWeather] = useState({
    temperature: '--',
    humidity: '--',
    rain: '--',
    alert: '',
  });

  const API_KEY = '6cfae7c53c635b12da2fa13d3955b3b5';

  const getLocationAndWeather = async () => {
    try {
      let { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permission Denied', 'Location access is needed for weather updates.');
        return;
      }

      let loc = await Location.getCurrentPositionAsync({});
      setLocation(loc.coords);

      // Reverse geocode to get city name
      let [place] = await Location.reverseGeocodeAsync({
        latitude: loc.coords.latitude,
        longitude: loc.coords.longitude,
      });

      const cityName = place.city || place.name || 'Unknown';
      setCity(cityName);
      fetchWeatherByCoords(loc.coords.latitude, loc.coords.longitude);
    } catch (err) {
      console.error('Error fetching location/weather:', err);
    }
  };

  const fetchWeatherByCoords = async (lat, lon) => {
    const URL = `https://api.openweathermap.org/data/2.5/weather?lat=${lat}&lon=${lon}&appid=${API_KEY}&units=metric`;

    try {
      const res = await axios.get(URL);
      const data = res.data;
      const rain = data.rain ? data.rain['1h'] || 0 : 0;

      setWeather({
        temperature: data.main.temp,
        humidity: data.main.humidity,
        rain,
        alert:
          rain > 0.1
            ? 'Moderate rain expected in the next 24 hours. Take necessary precautions.'
            : '',
      });
    } catch (error) {
      console.error('Weather API error:', error);
    }
  };

  useEffect(() => {
    getLocationAndWeather();
  }, []);

  const handleMenuPress = (item) => {
    setMenuVisible(false);
    switch (item) {
      case 'Home':
        navigation.navigate('Home');
        break;
      case 'Reminders':
        navigation.navigate('Reminders');
        break;
      case 'Weather':
        navigation.navigate('Weather');
        break;
      case 'Farm & Livestock':
        navigation.navigate('FarmDatabase');
        break;
      case 'Animal Records':
        navigation.navigate('AnimalRecordsScreen');
        break;
      default:
        alert(`${item} clicked`);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => setMenuVisible(true)}>
          <Ionicons name="menu" size={24} color="#000" />
        </TouchableOpacity>
        <Text style={styles.title}>Weather Forecast</Text>
      </View>

      <Text style={styles.sectionTitle}>City: {city}</Text>
      <Text style={styles.sectionTitle}>Current Conditions</Text>

      <View style={styles.conditionsGrid}>
        <View style={styles.box}>
          <Text style={styles.boxLabel}>Temperature</Text>
          <Text style={styles.boxValue}>{weather.temperature}°C</Text>
        </View>
        <View style={styles.box}>
          <Text style={styles.boxLabel}>Rain Forecast</Text>
          <Text style={styles.boxValue}>{weather.rain * 100}%</Text>
        </View>
        <View style={[styles.box, { width: '100%' }]}>
          <Text style={styles.boxLabel}>Humidity</Text>
          <Text style={styles.boxValue}>{weather.humidity}%</Text>
        </View>
      </View>

      <Text style={styles.sectionTitle}>Alerts</Text>
      <View style={styles.alertBox}>
        <Ionicons name="rainy-outline" size={24} />
        <View style={{ marginLeft: 10 }}>
          <Text style={{ fontWeight: 'bold' }}>Rain Alert</Text>
          <Text style={{ color: '#4CAF50' }}>
            {weather.alert || 'No alerts for now.'}
          </Text>
        </View>
      </View>

      <Text style={styles.sectionTitle}>Voice Input</Text>
      <TextInput
        style={styles.input}
        placeholder="Ask a question (e.g., Will it rain tomorrow?)"
        placeholderTextColor="#999"
      />
      <TouchableOpacity style={styles.voiceBtn}>
        <Ionicons name="mic" size={24} color="#fff" />
      </TouchableOpacity>

      <Modal transparent={true} visible={menuVisible} animationType="slide">
        <Pressable
          style={styles.modalOverlay}
          onPress={() => setMenuVisible(false)}
        >
          <View style={styles.menu}>
            {[
              'Home',
              'Market Prices',
              'Weather',
              'Reminders',
              'Farm & Livestock',
              'Animal Records',
              'Govt Schemes',
            ].map((item, index) => (
              <TouchableOpacity
                key={index}
                style={styles.menuItem}
                onPress={() => handleMenuPress(item)}
              >
                <Text style={styles.menuText}>{item}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </Pressable>
      </Modal>
    </SafeAreaView>
  );
};

export default Weather;

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: '#fff',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
    marginTop: 20,
  },
  title: {
    fontSize: 18,
    fontWeight: 'bold',
    marginLeft: 10,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginVertical: 10,
  },
  conditionsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  box: {
    width: '48%',
    backgroundColor: '#E8F5E9',
    padding: 15,
    borderRadius: 10,
    marginBottom: 10,
  },
  boxLabel: {
    color: '#333',
  },
  boxValue: {
    fontSize: 20,
    fontWeight: 'bold',
  },
  alertBox: {
    flexDirection: 'row',
    backgroundColor: '#F1F8E9',
    padding: 15,
    borderRadius: 10,
    alignItems: 'flex-start',
    marginBottom: 20,
  },
  input: {
    backgroundColor: '#F1F1F1',
    borderRadius: 10,
    padding: 15,
    marginTop: 10,
    color: '#000',
  },
  voiceBtn: {
    backgroundColor: '#4CAF50',
    borderRadius: 50,
    padding: 15,
    position: 'absolute',
    bottom: 20,
    right: 20,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.3)',
    justifyContent: 'flex-start',
  },
  menu: {
    backgroundColor: '#fff',
    paddingVertical: 20,
    paddingHorizontal: 15,
    borderBottomRightRadius: 10,
    borderBottomLeftRadius: 10,
  },
  menuItem: {
    paddingVertical: 12,
    borderBottomColor: '#ddd',
    borderBottomWidth: 1,
  },
  menuText: {
    fontSize: 16,
  },
});
