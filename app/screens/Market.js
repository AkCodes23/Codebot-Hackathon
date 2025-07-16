import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
  FlatList,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import i18n from '../i18n';

const MarketPrice = ({ navigation }) => {
  const vegetables = [
    { emoji: '🍅', key: 'tomatoes', price: '₹30/kg' },
    { emoji: '🥔', key: 'potatoes', price: '₹25/kg' },
    { emoji: '🧅', key: 'onions', price: '₹28/kg' },
    { emoji: '🥕', key: 'carrots', price: '₹35/kg' },
    { emoji: '🫘', key: 'beans', price: '₹40/kg' },
    { emoji: '🥬', key: 'cabbage', price: '₹22/kg' },
  ];

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.toggleDrawer()}>
          <Ionicons name="menu" size={24} color="#000" />
        </TouchableOpacity>
        <Text style={styles.title}>{i18n.t('market_prices')}</Text>
      </View>

      {/* Section Title */}
      <Text style={styles.subHeading}>{i18n.t('common_vegetables')}</Text>

      {/* Vegetable List */}
      <FlatList
        data={vegetables}
        keyExtractor={(item) => item.key}
        numColumns={2}
        columnWrapperStyle={{ justifyContent: 'space-between' }}
        contentContainerStyle={{ paddingBottom: 40 }}
        renderItem={({ item }) => (
          <View style={styles.card}>
            <Text style={styles.emoji}>{item.emoji}</Text>
            <Text style={styles.vegName}>{i18n.t(item.key)}</Text>
            <Text style={styles.price}>{item.price}</Text>
          </View>
        )}
      />
    </SafeAreaView>
  );
};

export default MarketPrice;

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingHorizontal: 20,
    paddingTop: 50,
    backgroundColor: '#fff',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 20,
  },
  title: {
    fontSize: 18,
    fontWeight: '600',
    marginLeft: 10,
  },
  subHeading: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 12,
  },
  card: {
    backgroundColor: '#F5F8F2',
    width: '47%',
    borderRadius: 10,
    padding: 15,
    marginBottom: 20,
    alignItems: 'center',
  },
  emoji: {
    fontSize: 36,
    marginBottom: 8,
  },
  vegName: {
    fontWeight: '600',
    fontSize: 14,
    color: '#333',
  },
  price: {
    fontSize: 13,
    color: '#666',
    marginTop: 5,
  },
});
