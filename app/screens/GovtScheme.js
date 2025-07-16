import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  SafeAreaView,
  Modal,
  Pressable,
  Linking,
} from 'react-native';
import { Ionicons, MaterialIcons, Entypo, FontAwesome5 } from '@expo/vector-icons';
import i18n from '../i18n';

const GovtSchemesScreen = ({ navigation }) => {
  const [menuVisible, setMenuVisible] = useState(false);

  const menuItems = [
    { label: i18n.t('home'), route: 'Home' },
    { label: i18n.t('market_prices'), route: 'Market' },
    { label: i18n.t('weather'), route: 'Weather' },
    { label: i18n.t('reminders'), route: 'Reminders' },
    { label: i18n.t('farm_livestock'), route: 'FarmDatabase' },
    { label: i18n.t('animal_records'), route: 'AnimalRecordsScreen' },
    { label: i18n.t('govt_schemes'), route: 'GovtScheme' },
  ];

  const schemes = [
    {
      title: 'Agriwelfare',
      description: i18n.t('scheme_agri_desc'),
      buttonKey: 'apply',
      site: 'https://agriwelfare.gov.in/',
      icon: <FontAwesome5 name="hands-helping" size={22} color="#000" />,
    },
    {
      title: 'Farmers portal',
      description: i18n.t('scheme_farmers_desc'),
      buttonKey: 'learn_more',
      site: 'https://www.india.gov.in/farmers-portal',
      icon: <Ionicons name="shield-checkmark-outline" size={24} color="#000" />,
    },
    {
      title: 'Indian Council of Agricultural Research',
      description: i18n.t('scheme_irrigation_desc'),
      buttonKey: 'learn_more',
      site: 'http://icar.org.in/',
      icon: <MaterialIcons name="opacity" size={24} color="#000" />,
    },
    {
      title: 'Department of Agriculture (Andhra Pradesh)',
      description: i18n.t('scheme_organic_desc'),
      buttonKey: 'apply',
      site: 'https://agriculture.ap.gov.in/home',
      icon: <Entypo name="leaf" size={24} color="#000" />,
    },
  ];

  const handleMenuPress = (route) => {
    setMenuVisible(false);
    navigation.navigate(route);
  };

  return (
    <SafeAreaView style={styles.container}>
      {/* Header with Menu Icon */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => setMenuVisible(true)} style={styles.menuIcon}>
          <Ionicons name="menu" size={24} color="black" />
        </TouchableOpacity>
        <Text style={styles.heading}>{i18n.t('govt_schemes')}</Text>
      </View>

      {/* Filter Tags (Optional UI) */}
      <View style={styles.filters}>
        <TouchableOpacity style={styles.filterButton}>
          <Text style={styles.filterText}>Location ⌄</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.filterButton}>
          <Text style={styles.filterText}>Crop Type ⌄</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.filterButton}>
          <Text style={styles.filterText}>Income Level ⌄</Text>
        </TouchableOpacity>
      </View>

      {/* Menu Modal */}
      <Modal visible={menuVisible} transparent animationType="fade">
        <Pressable style={styles.menuOverlay} onPress={() => setMenuVisible(false)}>
          <View style={styles.menu}>
            {menuItems.map((item) => (
              <TouchableOpacity
                key={item.route}
                onPress={() => handleMenuPress(item.route)}
                style={styles.menuItem}
              >
                <Text style={styles.menuText}>{item.label}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </Pressable>
      </Modal>

      {/* Government Scheme Cards */}
      <ScrollView style={styles.schemeList}>
        {schemes.map((scheme, index) => (
          <View key={index} style={styles.schemeCard}>
            <View style={styles.iconBox}>{scheme.icon}</View>
            <View style={{ flex: 1 }}>
              <Text style={styles.schemeTitle}>{scheme.title}</Text>
              <Text style={styles.schemeDesc}>{scheme.description}</Text>
              <Text style={styles.siteName}>
                {new URL(scheme.site).hostname.replace('www.', '')}
              </Text>
            </View>
            <TouchableOpacity
              style={styles.schemeButton}
              onPress={() => Linking.openURL(scheme.site)}
            >
              <Text>{i18n.t(scheme.buttonKey)}</Text>
            </TouchableOpacity>
          </View>
        ))}
      </ScrollView>

      {/* Mic Button that opens external voice assistant URL */}
      <TouchableOpacity
        style={styles.micButton}
        onPress={() => Linking.openURL('https://jnmrg673-8501.inc1.devtunnels.ms/')}
      >
        <Ionicons name="mic" size={28} color="#fff" />
      </TouchableOpacity>
    </SafeAreaView>
  );
};

export default GovtSchemesScreen;

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff', padding: 16, paddingTop: 40 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    height: 60,
    position: 'relative',
    marginBottom: 10,
  },
  menuIcon: {
    position: 'absolute',
    left: 0,
    paddingHorizontal: 10,
    marginTop: 15,
  },
  heading: {
    fontSize: 20,
    fontWeight: 'bold',
    textAlign: 'center',
    marginVertical: 10,
    marginTop: 15,
  },
  filters: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  filterButton: {
    backgroundColor: '#EAF2E3',
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 8,
  },
  filterText: {
    fontSize: 14,
    color: '#333',
  },
  schemeList: {
    flex: 1,
  },
  schemeCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F5F8F2',
    borderRadius: 10,
    padding: 12,
    marginBottom: 12,
  },
  iconBox: {
    backgroundColor: '#E0EED0',
    borderRadius: 8,
    padding: 10,
    marginRight: 12,
  },
  schemeTitle: {
    fontWeight: 'bold',
    fontSize: 15,
  },
  schemeDesc: {
    color: '#555',
    fontSize: 13,
    marginTop: 2,
  },
  siteName: {
    fontSize: 12,
    color: '#999',
    marginTop: 4,
  },
  schemeButton: {
    backgroundColor: '#EDF1E6',
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 6,
    alignSelf: 'center',
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
