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
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTranslation } from 'react-i18next';

const Help = ({ navigation }) => {
  const { t } = useTranslation();
  const [expandedIndex, setExpandedIndex] = useState(null);
  const [menuVisible, setMenuVisible] = useState(false);

  const faqList = [
    ['faq1_q', 'faq1_a'],
    ['faq2_q', 'faq2_a'],
    ['faq3_q', 'faq3_a'],
    ['faq5_q', 'faq5_a'],
    ['faq6_q', 'faq6_a'],
    ['faq7_q', 'faq7_a'],
    ['faq8_q', 'faq8_a'],
    ['faq9_q', 'faq9_a'],
    ['faq10_q', 'faq10_a'],
  ];

  const menuItems = [
    { labelKey: 'home', route: 'Home' },
    { labelKey: 'market_prices', route: 'Market' },
    { labelKey: 'weather', route: 'Weather' },
    { labelKey: 'reminders', route: 'Reminders' },
    { labelKey: 'farm_livestock', route: 'FarmDatabase' },
    { labelKey: 'animal_records', route: 'AnimalRecordsScreen' },
    { labelKey: 'govt_schemes', route: 'GovtScheme' },
  ];

  const toggleAnswer = (index) => {
    setExpandedIndex(expandedIndex === index ? null : index);
  };

  const handleMenuPress = (route) => {
    setMenuVisible(false);
    navigation.navigate(route);
  };

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => setMenuVisible(true)} style={styles.menuIcon}>
          <Ionicons name="menu" size={24} color="black" />
        </TouchableOpacity>
        <Text style={styles.heading}>{t('faqs_title')}</Text>
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
                <Text style={styles.menuText}>{t(item.labelKey)}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </Pressable>
      </Modal>

      {/* FAQs */}
      <ScrollView style={styles.faqList}>
        {faqList.map(([q, a], index) => (
          <View key={q} style={styles.faqCard}>
            <TouchableOpacity onPress={() => toggleAnswer(index)}>
              <Text style={styles.question}>• {t(q)}</Text>
            </TouchableOpacity>
            {expandedIndex === index && (
              <Text style={styles.answer}>{t(a)}</Text>
            )}
          </View>
        ))}
      </ScrollView>

      
    </SafeAreaView>
  );
};

export default Help;

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
    padding: 16,
    paddingTop: 40,
  },
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
  left: 2,
  top: 18,
},
heading: {
  fontSize: 20
  ,
  fontWeight: 'bold',
  color: 'black',
  marginLeft: 20,
},
  faqList: {
    flex: 1,
  },
  faqCard: {
    backgroundColor: '#F5F8F2',
    borderRadius: 10,
    padding: 12,
    marginBottom: 12,
    borderLeftWidth: 4,
    borderLeftColor: '#3CB043',
  },
  question: {
    fontSize: 16,
    fontWeight: '600',
    color: '#205200',
  },
  answer: {
    fontSize: 14,
    color: '#444',
    marginTop: 8,
    lineHeight: 20,
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
