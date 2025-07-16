import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  TouchableOpacity,
  Modal,
  Pressable,
  Linking,
  ScrollView,
} from 'react-native';
import { Picker } from '@react-native-picker/picker';
import { Ionicons } from '@expo/vector-icons';
import { useTranslation } from 'react-i18next';

const CropAdvice = ({ navigation }) => {
  const { t } = useTranslation();
  const [selectedCrop, setSelectedCrop] = useState('Rice');
  const [menuVisible, setMenuVisible] = useState(false);

  const advisoryData = {
    Rice: [
      { labelKey: 'site_crri', site: 'https://crri.icar.gov.in/' },
      { labelKey: 'site_drd', site: 'https://drdpat.bih.nic.in/' },
      { labelKey: 'site_pau', site: 'https://www.pau.edu/' },
      { labelKey: 'site_angrau', site: 'https://angrau.ac.in/' },
    ],
    Wheat: [
      { labelKey: 'site_iiwbr', site: 'https://iiwbr.icar.gov.in/' },
      { labelKey: 'site_dwd', site: 'https://dwd.dacnet.nic.in/' },
      { labelKey: 'site_pau', site: 'https://www.pau.edu/' },
      { labelKey: 'site_ccshau', site: 'https://www.hau.ac.in/' },
    ],
    Cotton: [
      { labelKey: 'site_cicr', site: 'https://cicr.org.in/' },
      { labelKey: 'site_dcd', site: 'https://dcd.dacnet.nic.in/' },
      { labelKey: 'site_mpkv', site: 'https://mpkv.ac.in/' },
      { labelKey: 'site_svpuat', site: 'https://www.svbpmeerut.ac.in/' },
    ],
    Sugarcane: [
      { labelKey: 'site_iisr', site: 'https://iiserkol.ac.in/' },
      { labelKey: 'site_sbi', site: 'https://sugarcane.icar.gov.in/' },
      { labelKey: 'site_upcar', site: 'http://upcaronline.org/' },
      { labelKey: 'site_mpkv', site: 'https://mpkv.ac.in/' },
    ],
    Corn: [
      { labelKey: 'site_iimr', site: 'https://iimr.icar.gov.in/' },
      { labelKey: 'site_dmd', site: 'https://dmd.dacnet.nic.in/' },
      { labelKey: 'site_uasb', site: 'https://uasbangalore.edu.in/' },
      { labelKey: 'site_rau', site: 'https://www.raubikaner.org/' },
    ],
  };

  const cropList = Object.keys(advisoryData);

  const handleMenuPress = (route) => {
    setMenuVisible(false);
    navigation.navigate(route);
  };

  const openLink = (url) => {
    Linking.openURL(url);
  };

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => setMenuVisible(true)} style={styles.menuIcon}>
          <Ionicons name="menu" size={24} color="black" />
        </TouchableOpacity>
        <Text style={styles.heading}>{t('crop_advice_title')}</Text>
      </View>

      {/* Menu Modal */}
      <Modal visible={menuVisible} transparent animationType="fade">
        <Pressable style={styles.menuOverlay} onPress={() => setMenuVisible(false)}>
          <View style={styles.menu}>
            {[
              { labelKey: 'home', route: 'Home' },
              { labelKey: 'market_prices', route: 'Market' },
              { labelKey: 'weather', route: 'Weather' },
              { labelKey: 'reminders', route: 'Reminders' },
              { labelKey: 'farm_livestock', route: 'FarmDatabase' },
              { labelKey: 'animal_records', route: 'AnimalRecordsScreen' },
              { labelKey: 'govt_schemes', route: 'GovtScheme' },
            ].map((item) => (
              <TouchableOpacity
                key={item.route}
                onPress={() => handleMenuPress(item.route)}
                style={styles.menuItem}
              >
                <Text style={styles.menuText}>{t(item.labelKey)}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </Pressable>
      </Modal>

      {/* Crop Picker */}
      <View style={styles.pickerContainer}>
        <Picker
          selectedValue={selectedCrop}
          onValueChange={(itemValue) => setSelectedCrop(itemValue)}
          style={styles.picker}
          dropdownIconColor="#205200"
        >
          {cropList.map((crop) => (
            <Picker.Item key={crop} label={crop} value={crop} />
          ))}
        </Picker>
      </View>

      {/* Advisory Links */}
      <ScrollView style={{ flex: 1 }}>
        {advisoryData[selectedCrop].map((item, index) => (
          <View key={index} style={styles.adviceCard}>
            <View style={{ flex: 1 }}>
              <Text style={styles.sourceName}>{t(item.labelKey)}</Text>
              <Text style={styles.url}>
                {new URL(item.site).hostname.replace('www.', '')}
              </Text>
            </View>
            <TouchableOpacity
              style={styles.learnButton}
              onPress={() => openLink(item.site)}
            >
              <Text style={{ color: '#205200' }}>{t('learn_more')}</Text>
            </TouchableOpacity>
          </View>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
};

export default CropAdvice;

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff', padding: 16, paddingTop: 40 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
    marginBottom: 10,
  },
  menuIcon: {
    position: 'absolute',
    left: 0,
    paddingHorizontal: 10,
    marginTop: 20,
  },
  heading: {
    fontSize: 20,
    fontWeight: 'bold',
    textAlign: 'center',
    marginTop: 20,
  },
  pickerContainer: {
    borderWidth: 1,
    borderColor: '#d0e4ba',
    borderRadius: 10,
    marginBottom: 16,
    overflow: 'hidden',
  },
  picker: {
    height: 50,
    color: '#205200',
  },
  adviceCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F5F8F2',
    borderRadius: 10,
    padding: 12,
    marginBottom: 12,
    borderLeftWidth: 4,
    borderLeftColor: '#3CB043',
  },
  sourceName: {
    fontWeight: 'bold',
    fontSize: 15,
    color: '#205200',
  },
  url: {
    fontSize: 12,
    color: '#888',
    marginTop: 4,
  },
  learnButton: {
    backgroundColor: '#EDF1E6',
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderRadius: 6,
    marginLeft: 10,
  },
  menuOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.2)',
    justifyContent: 'flex-start',
    paddingTop: 60,
    paddingHorizontal: 20,
  },
  menu: {
    backgroundColor: '#fff',
    borderRadius: 10,
    elevation: 5,
    padding: 10,
  },
  menuItem: {
    paddingVertical: 10,
    paddingHorizontal: 15,
  },
  menuText: {
    fontSize: 16,
  },
});
