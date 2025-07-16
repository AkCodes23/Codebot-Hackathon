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
  Linking,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import axios from 'axios';
import * as Location from 'expo-location';
import i18n from '../i18n';

const Weather = ({ navigation }) => {
  const [menuVisible, setMenuVisible] = useState(false);
  const [location, setLocation] = useState(null);
  const [city, setCity] = useState(i18n.t('fetching'));
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
        Alert.alert(i18n.t('permission_denied'), i18n.t('location_permission_needed'));
        return;
      }

      let loc = await Location.getCurrentPositionAsync({});
      setLocation(loc.coords);

      let [place] = await Location.reverseGeocodeAsync({
        latitude: loc.coords.latitude,
        longitude: loc.coords.longitude,
      });

      const cityName = place.city || place.name || i18n.t('unknown');
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
        alert: rain > 0.1 ? i18n.t('moderate_rain_warning') : '',
      });
    } catch (error) {
      console.error('Weather API error:', error);
    }
  };

  useEffect(() => {
    getLocationAndWeather();
  }, []);

  const menuItems = [
    { labelKey: 'home', route: 'Home' },
    { labelKey: 'market_prices', route: 'Market' },
    { labelKey: 'weather', route: 'Weather' },
    { labelKey: 'reminders', route: 'Reminders' },
    { labelKey: 'farm_livestock', route: 'FarmDatabase' },
    { labelKey: 'animal_records', route: 'AnimalRecordsScreen' },
    { labelKey: 'govt_schemes', route: 'GovtScheme' },
  ];

  const handleMenuPress = (route) => {
    setMenuVisible(false);
    navigation.navigate(route);
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => setMenuVisible(true)}>
          <Ionicons name="menu" size={24} color="#000" />
        </TouchableOpacity>
        <Text style={styles.title}>{i18n.t('weather_forecast')}</Text>
      </View>

      <Text style={styles.sectionTitle}>{i18n.t('city')}: {city}</Text>
      <Text style={styles.sectionTitle}>{i18n.t('current_conditions')}</Text>

      <View style={styles.conditionsGrid}>
        <View style={styles.box}>
          <Text style={styles.boxLabel}>{i18n.t('temperature')}</Text>
          <Text style={styles.boxValue}>{weather.temperature}°C</Text>
        </View>
        <View style={styles.box}>
          <Text style={styles.boxLabel}>{i18n.t('rain_forecast')}</Text>
          <Text style={styles.boxValue}>{weather.rain * 100}%</Text>
        </View>
        <View style={[styles.box, { width: '100%' }]}>
          <Text style={styles.boxLabel}>{i18n.t('humidity')}</Text>
          <Text style={styles.boxValue}>{weather.humidity}%</Text>
        </View>
      </View>

      <Text style={styles.sectionTitle}>{i18n.t('alerts')}</Text>
      <View style={styles.alertBox}>
        <Ionicons name="rainy-outline" size={24} />
        <View style={{ marginLeft: 10 }}>
          <Text style={{ fontWeight: 'bold' }}>{i18n.t('rain_alert')}</Text>
          <Text style={{ color: '#4CAF50' }}>
            {weather.alert || i18n.t('no_alerts')}
          </Text>
        </View>
      </View>

      <Text style={styles.sectionTitle}>{i18n.t('voice_input')}</Text>
      <TextInput
        style={styles.input}
        placeholder={i18n.t('ask_weather_placeholder')}
        placeholderTextColor="#999"
      />

      <TouchableOpacity
        style={styles.micButton}
        onPress={() => Linking.openURL('https://jnmrg673-8501.inc1.devtunnels.ms/')}
      >
        <Ionicons name="mic" size={28} color="#fff" />
      </TouchableOpacity>

      <Modal transparent={true} visible={menuVisible} animationType="slide">
        <Pressable style={styles.modalOverlay} onPress={() => setMenuVisible(false)}>
          <View style={styles.menu}>
            {menuItems.map((item, index) => (
              <TouchableOpacity
                key={index}
                style={styles.menuItem}
                onPress={() => handleMenuPress(item.route)}
              >
                <Text style={styles.menuText}>{i18n.t(item.labelKey)}</Text>
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
  micButton: {
    position: 'absolute',
    bottom: 30,
    right: 30,
    backgroundColor: '#3CB043',
    width: 56,
    height: 56,
    borderRadius: 28,
    alignItems: 'center',
    justifyContent: 'center',
    elevation: 5,
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
