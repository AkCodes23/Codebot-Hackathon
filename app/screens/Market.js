import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
  Modal,
} from 'react-native';
import { LineChart } from 'react-native-svg-charts';
import { Ionicons } from '@expo/vector-icons';
import axios from 'axios';

const Market = ({ navigation }) => {
  const [price, setPrice] = useState(2.5);
  const [change, setChange] = useState(5);
  const [trendData, setTrendData] = useState([2.4, 2.6, 2.5, 2.7, 2.3, 2.8, 2.5]);
  const [selectedVeggie, setSelectedVeggie] = useState('Tomatoes');
  const [menuVisible, setMenuVisible] = useState(false);

  const menuItems = [
    'Dashboard',
    'Crop Disease Prediction',
    'Market Prices',
    'Reminders',
    'Weather',
    'Govt Schemes',
  ];

  const veggies = [
    { name: 'Tomatoes', icon: '🍅' },
    { name: 'Potatoes', icon: '🥔' },
    { name: 'Onions', icon: '🧅' },
    { name: 'Carrots', icon: '🥕' },
  ];

  useEffect(() => {
    fetchMarketData(selectedVeggie);
  }, [selectedVeggie]);

  const fetchMarketData = async (veggie) => {
    try {
      const res = {
        data: {
          price: 2.5 + Math.random() * 0.5,
          change: Math.floor(Math.random() * 10),
          trend: Array.from({ length: 10 }, () => 2.3 + Math.random() * 0.5),
        },
      };
      setPrice(res.data.price.toFixed(2));
      setChange(res.data.change);
      setTrendData(res.data.trend);
    } catch (error) {
      console.error('API error:', error);
    }
  };

  const handleMenuPress = (item) => {
    setMenuVisible(false);
    switch (item) {
      case 'Crop Disease Prediction':
        navigation.navigate('CropDisease');
        break;
      case 'Market Prices':
        navigation.navigate('Market');
        break;
      case 'Weather':
        navigation.navigate('Weather');
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
        <Text style={styles.title}>Market Prices</Text>
      </View>

      <Text style={styles.label}>Select</Text>
      <View style={styles.dropdown}>
        <Text style={styles.selectedVeggie}>{selectedVeggie}</Text>
      </View>

      <View style={styles.priceBox}>
        <Text style={styles.priceText}>${price}/kg</Text>
        <Text style={styles.subText}>
          Last 30 Days <Text style={{ color: 'green' }}>+{change}%</Text>
        </Text>

        <LineChart
          style={{ height: 120 }}
          data={trendData}
          svg={{ stroke: 'green', strokeWidth: 2 }}
          contentInset={{ top: 10, bottom: 10 }}
        />
        <View style={styles.weeks}>
          <Text>1W</Text>
          <Text>2W</Text>
          <Text>3W</Text>
          <Text>4W</Text>
        </View>
      </View>

      <Text style={styles.commonText}>Common Vegetables</Text>
      <View style={styles.vegGrid}>
        {veggies.map((item) => (
          <TouchableOpacity
            key={item.name}
            style={[
              styles.vegBox,
              selectedVeggie === item.name && styles.selectedVegBox,
            ]}
            onPress={() => setSelectedVeggie(item.name)}
          >
            <Text style={styles.vegIcon}>{item.icon}</Text>
            <Text>{item.name}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <TouchableOpacity style={styles.voiceBtn}>
        <Ionicons name="mic" size={24} color="#fff" />
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
};

export default Market;

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: '#fff',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginBottom: 10,
    marginTop: 20,
  },
  title: {
    fontSize: 18,
    fontWeight: 'bold',
    marginLeft: 10,
  },
  label: {
    fontSize: 16,
    marginTop: 10,
    marginBottom: 5,
  },
  dropdown: {
    backgroundColor: '#E8F5E9',
    borderRadius: 8,
    padding: 10,
    marginBottom: 20,
  },
  selectedVeggie: {
    fontSize: 16,
    fontWeight: '600',
    color: '#2E7D32',
  },
  priceBox: {
    marginBottom: 20,
  },
  priceText: {
    fontSize: 24,
    fontWeight: 'bold',
  },
  subText: {
    fontSize: 14,
    color: '#666',
    marginBottom: 10,
  },
  weeks: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 5,
    marginTop: 5,
  },
  commonText: {
    fontSize: 16,
    fontWeight: '600',
    marginVertical: 10,
  },
  vegGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  vegBox: {
    width: '48%',
    backgroundColor: '#F1F8E9',
    padding: 15,
    borderRadius: 10,
    marginBottom: 10,
    alignItems: 'center',
  },
  selectedVegBox: {
    backgroundColor: '#C8E6C9',
  },
  vegIcon: {
    fontSize: 24,
    marginBottom: 5,
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
