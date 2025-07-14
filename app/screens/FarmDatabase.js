import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Modal,
  TextInput,
  ScrollView,
  Image,
} from 'react-native';
import { Audio } from 'expo-av';
import * as ImagePicker from 'expo-image-picker';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import i18n from '../i18n';

const FarmDatabase = () => {
  const navigation = useNavigation();

  const [langReady, setLangReady] = useState(false);
  const [selectedAnimal, setSelectedAnimal] = useState('');
  const [animalModalVisible, setAnimalModalVisible] = useState(false);
  const [menuVisible, setMenuVisible] = useState(false);
  const [animalData, setAnimalData] = useState({
    name: '',
    breed: '',
    weight: '',
    age: '',
    food: '',
    health: '',
    requirements: '',
    remarksUri: '',
    imageUri: '',
  });
  const [recording, setRecording] = useState(null);

  useEffect(() => {
    const loadLang = async () => {
      const lang = await AsyncStorage.getItem('appLang');
      if (lang) await i18n.changeLanguage(lang);
      setLangReady(true);
    };
    loadLang();
  }, []);

  if (!langReady) return <View style={{ flex: 1, backgroundColor: '#fff' }} />;

  const menuItems = [
    { label: i18n.t('home'), route: 'Home' },
    { label: i18n.t('market_prices'), route: 'Market' },
    { label: i18n.t('weather'), route: 'Weather' },
    { label: i18n.t('reminders'), route: 'Reminders' },
    { label: i18n.t('farm_livestock'), route: 'FarmDatabase' },
    { label: i18n.t('animal_records'), route: 'AnimalRecordsScreen' },
    { label: i18n.t('govt_schemes'), route: 'GovtScheme' },
  ];

  const animals = [
    { name: i18n.t('cow'), icon: '🐄' },
    { name: i18n.t('buffalo'), icon: '🐃' },
    { name: i18n.t('goat'), icon: '🐐' },
    { name: i18n.t('sheep'), icon: '🐑' },
    { name: i18n.t('pig'), icon: '🐖' },
    { name: i18n.t('horse'), icon: '🐎' },
  ];

  const recordAudio = async () => {
    const permission = await Audio.requestPermissionsAsync();
    if (permission.status !== 'granted') {
      alert(i18n.t('mic_permission_alert'));
      return;
    }

    if (recording) {
      await recording.stopAndUnloadAsync();
      const uri = recording.getURI();
      setAnimalData((prev) => ({ ...prev, remarksUri: uri }));
      setRecording(null);
      alert(i18n.t('recording_saved'));
    } else {
      const { recording: newRecording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      setRecording(newRecording);
    }
  };

  const pickImageFromGallery = async () => {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (permission.status !== 'granted') {
      alert(i18n.t('gallery_permission_alert'));
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.7,
    });

    if (!result.canceled) {
      setAnimalData((prev) => ({ ...prev, imageUri: result.assets[0].uri }));
    }
  };

  const takePhotoWithCamera = async () => {
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    if (permission.status !== 'granted') {
      alert(i18n.t('camera_permission_alert'));
      return;
    }

    const result = await ImagePicker.launchCameraAsync({ quality: 0.7 });

    if (!result.canceled) {
      setAnimalData((prev) => ({ ...prev, imageUri: result.assets[0].uri }));
    }
  };

  const saveAnimalData = async () => {
    const dataToSave = {
      animalType: selectedAnimal,
      timestamp: new Date().toISOString(),
      ...animalData,
    };

    try {
      const existing = await AsyncStorage.getItem('animalRecords');
      const parsed = existing ? JSON.parse(existing) : [];
      await AsyncStorage.setItem('animalRecords', JSON.stringify([...parsed, dataToSave]));

      alert(i18n.t('animal_data_saved'));
      setAnimalModalVisible(false);
      setAnimalData({
        name: '',
        breed: '',
        weight: '',
        age: '',
        food: '',
        health: '',
        requirements: '',
        remarksUri: '',
        imageUri: '',
      });
    } catch (e) {
      console.error('Saving error:', e);
    }
  };

  const handleMenuPress = (route) => {
    setMenuVisible(false);
    navigation.navigate(route);
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => setMenuVisible(true)}>
          <Ionicons name="menu" size={28} color="black" />
        </TouchableOpacity>
        <Text style={styles.heading}>{i18n.t('farm_livestock')}</Text>
      </View>

      {menuVisible && (
        <View style={styles.menuContainer}>
          {menuItems.map((item) => (
            <TouchableOpacity key={item.route} style={styles.menuItem} onPress={() => handleMenuPress(item.route)}>
              <Text style={styles.menuText}>{item.label}</Text>
            </TouchableOpacity>
          ))}
        </View>
      )}

      <View style={styles.animalRow}>
        {animals.map((animal) => (
          <TouchableOpacity
            key={animal.name}
            style={styles.animalIcon}
            onPress={() => {
              setSelectedAnimal(animal.name);
              setAnimalModalVisible(true);
            }}
          >
            <Text style={styles.icon}>{animal.icon}</Text>
            <Text style={styles.label}>{animal.name}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <TouchableOpacity
        onPress={() => navigation.navigate('AnimalRecordsScreen')}
        style={styles.recordsButtonButton}
      >
        <Text style={styles.recordsButtonText}>{i18n.t('view_records')}</Text>
      </TouchableOpacity>

      <Modal visible={animalModalVisible} transparent animationType="slide">
        <View style={styles.modalBackground}>
          <View style={styles.animalModal}>
            <Text style={styles.modalTitle}>{selectedAnimal} {i18n.t('details')}</Text>

            {['name', 'breed', 'weight', 'age', 'food', 'health', 'requirements'].map((field) => (
              <TextInput
                key={field}
                style={styles.modalInput}
                placeholder={i18n.t(field)}
                value={animalData[field]}
                onChangeText={(text) => setAnimalData((prev) => ({ ...prev, [field]: text }))}
              />
            ))}

            <View style={styles.imageButtons}>
              <TouchableOpacity onPress={pickImageFromGallery} style={styles.imageButton}>
                <Text style={{ color: '#fff' }}>{i18n.t('upload_image')}</Text>
              </TouchableOpacity>
              <TouchableOpacity onPress={takePhotoWithCamera} style={styles.imageButton}>
                <Text style={{ color: '#fff' }}>{i18n.t('take_photo')}</Text>
              </TouchableOpacity>
            </View>

            {animalData.imageUri && (
              <Image source={{ uri: animalData.imageUri }} style={{ width: 100, height: 100, alignSelf: 'center', marginVertical: 10, borderRadius: 8 }} />
            )}

            <TouchableOpacity onPress={recordAudio} style={styles.recordButton}>
              <Text style={{ color: '#fff' }}>
                {recording ? i18n.t('stop_recording') : i18n.t('record_remarks')}
              </Text>
            </TouchableOpacity>

            <View style={styles.modalButtons}>
              <TouchableOpacity onPress={saveAnimalData}>
                <Text style={{ color: '#4CAF50', fontWeight: 'bold' }}>{i18n.t('save')}</Text>
              </TouchableOpacity>
              <TouchableOpacity onPress={() => setAnimalModalVisible(false)}>
                <Text style={{ color: '#f44336', fontWeight: 'bold' }}>{i18n.t('cancel')}</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </ScrollView>
  );
};

export default FarmDatabase;

const styles = StyleSheet.create({
  container: { padding: 20, backgroundColor: '#fff', flexGrow: 1 },
  header: { flexDirection: 'row', alignItems: 'center', marginBottom: 15, marginTop: 20 },
  heading: { fontSize: 22, fontWeight: 'bold', marginLeft: 10, flex: 1 },
  menuContainer: {
    backgroundColor: '#fff',
    borderRadius: 8,
    elevation: 5,
    padding: 10,
    marginBottom: 15,
  },
  menuItem: {
    paddingVertical: 10,
  },
  menuText: {
    fontSize: 16,
  },
  animalRow: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-around', marginBottom: 30 },
  animalIcon: { alignItems: 'center', padding: 10, width: '30%', marginVertical: 10 },
  icon: { fontSize: 40 },
  label: { fontSize: 14, marginTop: 5 },
  modalBackground: { flex: 1, justifyContent: 'center', backgroundColor: 'rgba(0,0,0,0.3)' },
  animalModal: { backgroundColor: '#fff', margin: 20, padding: 20, borderRadius: 10, elevation: 5 },
  modalTitle: { fontSize: 18, fontWeight: 'bold', marginBottom: 10, textAlign: 'center' },
  modalInput: { borderBottomWidth: 1, borderColor: '#ccc', marginBottom: 12, paddingVertical: 5, fontSize: 14 },
  recordButton: { backgroundColor: '#4CAF50', padding: 12, alignItems: 'center', borderRadius: 6, marginBottom: 10 },
  modalButtons: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 10 },
  imageButtons: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 10 },
  imageButton: { backgroundColor: '#4CAF50', padding: 10, borderRadius: 6, width: '48%', alignItems: 'center' },
  recordsButtonButton: {
    backgroundColor: '#3cb371',
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 8,
    alignSelf: 'center',
    marginTop: 20,
  },
  recordsButtonText: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 16,
  },
});
