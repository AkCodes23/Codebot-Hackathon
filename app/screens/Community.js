import React from 'react';
import {
  View,
  Text,
  Button,
  StyleSheet,
  Linking,
  Alert,
} from 'react-native';

const Community = () => {
  const url = 'https://f584r3ct-8082.inc1.devtunnels.ms/';

  const handleOpenLink = async () => {
    try {
      const supported = await Linking.canOpenURL(url);
      if (supported) {
        await Linking.openURL(url);
      } else {
        Alert.alert('Unsupported URL', 'Cannot open this link.');
      }
    } catch (error) {
      Alert.alert('Error', 'Something went wrong while opening the link.');
      console.error('Linking error:', error);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Community</Text>
      <Button title="Open Community Portal" onPress={handleOpenLink} />
    </View>
  );
};

export default Community;

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    paddingTop: 60,
    backgroundColor: '#f5f5f5',
  },
  title: {
    fontSize: 22,
    fontWeight: 'bold',
    marginBottom: 20,
  },
});
