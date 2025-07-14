import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Image,
  TouchableOpacity,
  SafeAreaView,
  ScrollView,
  Modal,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import * as Speech from 'expo-speech';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';

export default function CropDisease({ navigation }) {
  const [imageUri, setImageUri] = useState(null);
  const [menuVisible, setMenuVisible] = useState(false);

  const menuItems = [
    'Dashboard',
    'Crop Disease Prediction',
    'Market Prices',
    'Reminders',
    'Weather',
    'Govt Schemes',
  ];

  const pickImage = async () => {
    const permissionResult = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (permissionResult.granted === false) {
      alert('Permission to access camera roll is required!');
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 1,
    });

    if (!result.canceled) {
      setImageUri(result.assets[0].uri);
    }
  };

  const readAloud = () => {
    const message =
      'Disease: Leaf Blight. Treatment: Apply a fungicide containing mancozeb or copper oxychloride. Ensure proper ventilation and avoid overcrowding of plants.';
    Speech.speak(message);
  };

  const handleScan = () => {
    alert('Scanning image...'); // Replace with model or API logic
  };

  const handleMenuPress = (item) => {
    setMenuVisible(false);
    switch (item) {
      case 'Crop Disease Prediction':
        navigation.navigate('CropDisease');
        break;
      case 'Weather':
        navigation.navigate('Weather');
        break;
      case 'Reminders':
      navigation.navigate('Reminders');
        break; 
      case 'Farm & Livestock':
        navigation.navigate('FarmDatabase');
        break;     
      default:
        alert(`${item} clicked`);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => setMenuVisible(true)}>
            <Ionicons name="menu" size={24} color="#000" />
          </TouchableOpacity>
          <Text style={styles.title}>Crop Disease Prediction</Text>
        </View>

        <Text style={styles.description}>
          Upload an image of the affected crop to get a disease prediction and treatment suggestions.
        </Text>

        <TouchableOpacity style={styles.uploadButton} onPress={pickImage}>
          <Text style={styles.uploadButtonText}>Upload Image</Text>
        </TouchableOpacity>

        {imageUri && (
          <>
            <Image source={{ uri: imageUri }} style={styles.image} />

            <TouchableOpacity style={styles.scanButton} onPress={handleScan}>
              <Text style={styles.scanButtonText}>Scan</Text>
            </TouchableOpacity>
          </>
        )}

        <View style={styles.resultsContainer}>
          <Text style={styles.resultHeading}>Results</Text>
          <Text style={styles.resultText}>
            <Text style={{ fontWeight: 'bold' }}>Disease:</Text> Leaf Blight
          </Text>
          <Text style={styles.resultText}>
            <Text style={{ fontWeight: 'bold' }}>Treatment:</Text> Apply a fungicide containing mancozeb or copper oxychloride.
          </Text>

          <TouchableOpacity style={styles.readAloudButton} onPress={readAloud}>
            <Ionicons name="volume-high" size={20} color="#000" />
            <Text style={styles.readAloudText}>Read Aloud</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>

      <TouchableOpacity style={styles.micButton}>
        <MaterialCommunityIcons name="microphone" size={30} color="#fff" />
      </TouchableOpacity>

      {/* Modal Menu */}
      <Modal
        transparent={true}
        visible={menuVisible}
        animationType="slide"
        onRequestClose={() => setMenuVisible(false)}
      >
        <TouchableOpacity style={styles.modalOverlay} onPress={() => setMenuVisible(false)}>
          <View style={styles.menu}>
            {menuItems.map((item, index) => (
              <TouchableOpacity
                key={index}
                style={styles.menuItem}
                onPress={() => handleMenuPress(item)}
              >
                <Text style={styles.menuText}>{item}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </TouchableOpacity>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 100,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
    marginTop: 20,
  },
  title: {
    fontSize: 18,
    fontWeight: '600',
    marginLeft: 20,
  },
  description: {
    fontSize: 14,
    marginBottom: 20,
    color: '#555',
  },
  uploadButton: {
    backgroundColor: '#e6f2e6',
    padding: 10,
    borderRadius: 10,
    alignItems: 'center',
    marginBottom: 25,
  },
  uploadButtonText: {
    color: '#333',
    fontWeight: '600',
  },
  image: {
    width: '100%',
    height: 250,
    borderRadius: 12,
    marginBottom: 20,
  },
  scanButton: {
    backgroundColor: '#e6f2e6',
    paddingVertical: 10,
    borderRadius: 10,
    alignItems: 'center',
    marginBottom: 20,
  },
  scanButtonText: {
    color: '#333',
    fontWeight: '600',
    fontSize: 16,
  },
  resultsContainer: {
    marginTop: 10,
  },
  resultHeading: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 5,
  },
  resultText: {
    fontSize: 14,
    marginBottom: 8,
    color: '#333',
  },
  readAloudButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f2f2f2',
    padding: 10,
    borderRadius: 8,
    alignSelf: 'center',
    width: 130,
    marginTop: 10,
  },
  readAloudText: {
    marginLeft: 6,
    fontWeight: '500',
  },
  micButton: {
    position: 'absolute',
    bottom: 25,
    right: 20,
    backgroundColor: '#3cb371',
    width: 55,
    height: 55,
    borderRadius: 30,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOpacity: 0.3,
    shadowRadius: 5,
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
