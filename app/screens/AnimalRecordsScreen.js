import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Alert,
  TextInput,
  Modal,
  Image,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Audio } from 'expo-av';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import i18n from '../i18n';

const AnimalRecordsScreen = () => {
  const [records, setRecords] = useState([]);
  const [editingIndex, setEditingIndex] = useState(null);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editData, setEditData] = useState({});
  const [sound, setSound] = useState(null);
  const [menuVisible, setMenuVisible] = useState(false);
  const navigation = useNavigation();

  const menuItems = [
    { label: i18n.t('home'), route: 'Home' },
    { label: i18n.t('market_prices'), route: 'Market' },
    { label: i18n.t('weather'), route: 'Weather' },
    { label: i18n.t('reminders'), route: 'Reminders' },
    { label: i18n.t('farm_livestock'), route: 'FarmDatabase' },
    { label: i18n.t('animal_records'), route: 'AnimalRecordsScreen' },
    { label: i18n.t('govt_schemes'), route: 'GovtScheme' },
  ];

  useEffect(() => {
    loadRecords();
    return () => {
      if (sound) sound.unloadAsync();
    };
  }, []);

  const loadRecords = async () => {
    const data = await AsyncStorage.getItem('animalRecords');
    setRecords(data ? JSON.parse(data) : []);
  };

  const deleteRecord = async (index) => {
    const updated = [...records];
    updated.splice(index, 1);
    await AsyncStorage.setItem('animalRecords', JSON.stringify(updated));
    setRecords(updated);
  };

  const saveEdit = async () => {
    const updated = [...records];
    updated[editingIndex] = { ...updated[editingIndex], ...editData };
    await AsyncStorage.setItem('animalRecords', JSON.stringify(updated));
    setRecords(updated);
    setEditModalVisible(false);
  };

  const openEdit = (item, index) => {
    setEditingIndex(index);
    setEditData(item);
    setEditModalVisible(true);
  };

  const playAudio = async (uri) => {
    try {
      if (!uri) return;
      const { sound } = await Audio.Sound.createAsync({ uri });
      setSound(sound);
      await sound.playAsync();
    } catch (error) {
      console.log('Audio playback error:', error);
    }
  };

  const handleMenuPress = (route) => {
    setMenuVisible(false);
    navigation.navigate(route);
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => setMenuVisible(true)}>
          <Ionicons name="menu" size={28} color="black" />
        </TouchableOpacity>
        <Text style={styles.heading}>{i18n.t('saved_animal_records')}</Text>
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

      <FlatList
        data={records}
        keyExtractor={(_, idx) => idx.toString()}
        renderItem={({ item, index }) => (
          <View style={styles.card}>
            <Text style={styles.animalTitle}>{item.name} ({item.animalType})</Text>
            <Text>{i18n.t('breed')}: {item.breed}</Text>
            <Text>{i18n.t('age')}: {item.age} | {i18n.t('weight')}: {item.weight}</Text>
            <Text>{i18n.t('food')}: {item.food}</Text>
            <Text>{i18n.t('health')}: {item.health}</Text>
            <Text>{i18n.t('requirements')}: {item.requirements}</Text>
            {item.imageUri ? (
              <Image source={{ uri: item.imageUri }} style={{ width: 100, height: 100, borderRadius: 10, marginTop: 10 }} />
            ) : null}
            {item.remarksUri ? (
              <TouchableOpacity onPress={() => playAudio(item.remarksUri)}>
                <Text style={styles.audioButton}>🔊 {i18n.t('play_remarks')}</Text>
              </TouchableOpacity>
            ) : null}
            <View style={styles.actions}>
              <TouchableOpacity onPress={() => openEdit(item, index)}>
                <Text style={styles.edit}>✏️ {i18n.t('edit')}</Text>
              </TouchableOpacity>
              <TouchableOpacity onPress={() =>
                Alert.alert(i18n.t('delete_entry'), i18n.t('are_you_sure'), [
                  { text: i18n.t('cancel') },
                  {
                    text: i18n.t('delete'),
                    onPress: () => deleteRecord(index),
                    style: 'destructive',
                  },
                ])
              }>
                <Text style={styles.delete}>🗑 {i18n.t('delete')}</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}
      />

      <Modal visible={editModalVisible} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modalBox}>
            <Text style={styles.modalTitle}>{i18n.t('edit')}</Text>
            {['name', 'breed', 'age', 'weight', 'food', 'health', 'requirements'].map((field) => (
              <TextInput
                key={field}
                placeholder={i18n.t(field)}
                value={editData[field]}
                onChangeText={(text) => setEditData((prev) => ({ ...prev, [field]: text }))}
                style={styles.input}
              />
            ))}
            <TouchableOpacity style={styles.saveButton} onPress={saveEdit}>
              <Text style={{ color: '#fff' }}>{i18n.t('save_changes')}</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </View>
  );
};


export default AnimalRecordsScreen;

const styles = StyleSheet.create({
  container: { padding: 20, backgroundColor: '#fff', flex: 1 },
  header: { flexDirection: 'row', alignItems: 'center', marginBottom: 15, marginTop: 20 },
  heading: { fontSize: 22, fontWeight: 'bold', marginLeft: 10 },
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
  card: { padding: 15, backgroundColor: '#F1F8E9', borderRadius: 10, marginBottom: 15 },
  animalTitle: { fontSize: 16, fontWeight: 'bold' },
  actions: { flexDirection: 'row', marginTop: 10, justifyContent: 'space-between' },
  edit: { color: '#2196F3' },
  delete: { color: '#f44336' },
  audioButton: { color: '#4CAF50', marginTop: 10 },
  modalOverlay: { flex: 1, justifyContent: 'center', backgroundColor: 'rgba(0,0,0,0.3)' },
  modalBox: { margin: 20, backgroundColor: '#fff', borderRadius: 10, padding: 20, elevation: 5 },
  modalTitle: { fontSize: 18, fontWeight: 'bold', marginBottom: 10, textAlign: 'center' },
  input: { borderBottomWidth: 1, borderColor: '#ccc', paddingVertical: 5, marginBottom: 12 },
  saveButton: { backgroundColor: '#4CAF50', padding: 10, borderRadius: 5, alignItems: 'center' },
});
