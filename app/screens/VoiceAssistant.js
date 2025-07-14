import React, { useEffect, useState } from 'react';
import { View, Text, Button, StyleSheet, ActivityIndicator, Alert } from 'react-native';

const VoiceAssistant = () => {
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchData = async () => {
    try {
      setLoading(true);
      const res = await fetch('https://jnmrg673-8501.inc1.devtunnels.ms/');
      
      if (!res.ok) {
        throw new Error(`HTTP error! Status: ${res.status}`);
      }

      const data = await res.text(); // Or use `.json()` if it's JSON
      setResponse(data);
    } catch (error) {
      console.error('Fetch error:', error);
      Alert.alert('Error', error.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(); // Fetch on mount
  }, []);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Voice Assistant Response</Text>
      {loading ? (
        <ActivityIndicator size="large" color="#007bff" />
      ) : (
        <Text style={styles.response}>{response || 'No response yet.'}</Text>
      )}
      <Button title="Refresh" onPress={fetchData} />
    </View>
  );
};

export default VoiceAssistant;

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
  response: {
    fontSize: 16,
    marginBottom: 20,
    color: '#333',
  },
});
