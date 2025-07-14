import React, { useState } from 'react';
import {
  View,
  Text,
  Image,
  TouchableOpacity,
  StyleSheet,
  Dimensions,
} from 'react-native';
import { Picker } from '@react-native-picker/picker';
import i18n from '../i18n';
import { useNavigation } from '@react-navigation/native';

const screen = Dimensions.get('window');

export default function LanguageScreen() {
  const [selectedLang, setSelectedLang] = useState(i18n.language || 'en');
  const navigation = useNavigation();

  const handleStart = () => {
    i18n.changeLanguage(selectedLang);
    navigation.navigate('WelcomeScreen', { selectedLang });
  };

  return (
    <View style={styles.container}>
      {/* Semi-transparent background overlay */}
      <View style={styles.backgroundOverlay} />

      {/* Semi-transparent Logo */}
      <Image
        source={require('../../assets/KisanVaani_logo.png')}
        style={styles.logo}
        resizeMode="contain"
      />

      {/* Foreground content */}
      <View style={styles.overlay}>
        <Text style={styles.label}>Choose your language</Text>

        <View style={styles.dropdown}>
          <Picker
            selectedValue={selectedLang}
            onValueChange={(itemValue) => setSelectedLang(itemValue)}
            style={styles.picker}
          >
            <Picker.Item label="English" value="en" />
            <Picker.Item label="हिंदी" value="hi" />
            <Picker.Item label="मराठी" value="mr" />
            <Picker.Item label="ಕನ್ನಡ" value="kn" />
            <Picker.Item label="தமிழ்" value="ta" />
            <Picker.Item label="తెలుగు" value="te" />
          </Picker>
        </View>

        <TouchableOpacity style={styles.button} onPress={handleStart}>
          <Text style={styles.buttonText}>Start</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#124936',
    alignItems: 'center',
    justifyContent: 'center',
  },
  backgroundOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(18, 73, 54, 0.6)', // #124936 with reduced opacity
    zIndex: -1,
  },
  logo: {
    width: screen.width * 0.95,
    height: screen.height * 0.5,
    opacity: 0.5, // 🔍 logo transparency here
    marginBottom: 10,
  },
  overlay: {
    width: '90%',
    alignItems: 'center',
    marginTop: 10,
  },
  label: {
    fontSize: 18,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 10,
  },
  dropdown: {
    width: '100%',
    borderWidth: 1,
    borderColor: '#fff',
    borderRadius: 5,
    marginBottom: 30,
    backgroundColor: '#ffffffee',
  },
  picker: {
    height: 50,
    width: '100%',
    color: '#000',
  },
  button: {
    backgroundColor: '#ffffff',
    paddingVertical: 12,
    paddingHorizontal: 30,
    borderRadius: 8,
  },
  buttonText: {
    color: '#124936',
    fontSize: 16,
    fontWeight: '600',
  },
});
