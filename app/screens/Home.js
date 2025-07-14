import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, SafeAreaView, Linking } from 'react-native';
import { Ionicons, MaterialIcons, FontAwesome5, Entypo, FontAwesome } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';

const features = [
  {
    title: 'Weather',
    subtitle: 'Check today’s weather',
    iconComponent: Ionicons,
    iconProps: { name: 'sunny-outline', size: 24, color: 'black' },
    screen: 'Weather',
  },
  {
    title: 'Crop Advisory',
    subtitle: 'Get expert advice',
    iconComponent: MaterialIcons,
    iconProps: { name: 'eco', size: 24, color: 'black' },
    screen: 'AnimalRecordsScreen',
  },
  {
    title: 'Market Prices',
    subtitle: 'Latest market trends',
    iconComponent: FontAwesome5,
    iconProps: { name: 'rupee-sign', size: 20, color: 'black' },
    screen: 'Market',
  },
  {
    title: 'Ask KisanVaani',
    subtitle: 'Your AI assistant',
    iconComponent: Ionicons,
    iconProps: { name: 'chatbubble-ellipses-outline', size: 22, color: 'black' },
    screen: 'VoiceAssistant', // special case handled below
  },
  {
    title: 'Community',
    subtitle: 'Connect with farmers',
    iconComponent: Ionicons,
    iconProps: { name: 'people-outline', size: 24, color: 'black' },
    screen: '',
  },
  {
    title: 'Help',
    subtitle: 'FAQs and support',
    iconComponent: Entypo,
    iconProps: { name: 'help-with-circle', size: 22, color: 'black' },
    screen: '',
  },
  {
    title: 'Livestock Database',
    subtitle: 'Track and manage animals',
    iconComponent: FontAwesome5,
    iconProps: { name: 'horse', size: 22, color: 'black' },
    screen: 'FarmDatabase',
  },
  {
    title: 'Govt Schemes',
    subtitle: 'Know available benefits',
    iconComponent: FontAwesome,
    iconProps: { name: 'institution', size: 22, color: 'black' },
    screen: 'GovtScheme',
  },
  {
    title: 'Reminders',
    subtitle: 'Manage farm tasks',
    iconComponent: Ionicons,
    iconProps: { name: 'alarm-outline', size: 22, color: 'black' },
    screen: 'Reminders',
  },
];

const KisanVaaniHome = () => {
  const navigation = useNavigation();

  const handlePress = (item) => {
    if (item.screen === 'VoiceAssistant') {
      Linking.openURL('https://ptjdr6h5-8501.inc1.devtunnels.ms/');
    } else if (item.screen) {
      navigation.navigate(item.screen);
    } else {
      console.log(`${item.title} pressed`);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.title}>KisanVaani</Text>
      <Text style={styles.greeting}>Welcome!</Text>

      <View style={styles.grid}>
        {features.map((item, idx) => {
          const Icon = item.iconComponent;
          return (
            <TouchableOpacity key={idx} style={styles.card} onPress={() => handlePress(item)}>
              <Icon {...item.iconProps} />
              <Text style={styles.cardTitle}>{item.title}</Text>
              <Text style={styles.cardSubtitle}>{item.subtitle}</Text>
            </TouchableOpacity>
          );
        })}
      </View>

      <TouchableOpacity style={styles.micButton} onPress={() => console.log('Voice input')}>
        <Ionicons name="mic" size={28} color="#fff" />
      </TouchableOpacity>
    </SafeAreaView>
  );
};

export default KisanVaaniHome;

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingTop: 50,
    paddingHorizontal: 20,
    backgroundColor: '#fff',
  },
  title: {
    fontSize: 20,
    fontWeight: '600',
    color: '#111',
  },
  greeting: {
    fontSize: 26,
    fontWeight: 'bold',
    marginVertical: 20,
    color: '#222',
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  card: {
    width: '47%',
    backgroundColor: '#F5F8F2',
    borderRadius: 12,
    padding: 15,
    marginBottom: 20,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginTop: 10,
  },
  cardSubtitle: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
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
});
